/* Somatic GPU hot path. The 48-byte ABI is three vec4<f32> values.
 * State is uploaded once, remains GPU-resident, and is paged to respect the
 * adapter's actual storage-binding limit. This is not zero-copy.
 * Scope: gravity + ground contact + restitution + tangential friction +
 * stress-dependent energy drain. It is not inter-cell collision or bond physics.
 */
const CELL_BYTES=48, FLOATS_PER_CELL=12, WORKGROUP_SIZE=256, MAX_DT=1/30;
const WGSL = String.raw\`
struct SomaticCell {
  position: vec4<f32>,
  velocity: vec4<f32>,
  state: vec4<f32>,
};
struct SimParams {
  dt: f32, gravity: f32, groundY: f32, restitution: f32,
  friction: f32, energyDrain: f32, cellCount: u32, _pad: u32,
};
@group(0) @binding(0) var<storage, read_write> cells: array<SomaticCell>;
@group(0) @binding(1) var<uniform> params: SimParams;
@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
  let i=gid.x;
  if(i>=params.cellCount || i>=arrayLength(&cells)){return;}
  var c=cells[i];
  let dt=clamp(params.dt,0.0,0.0333333333);
  let mass=max(c.position.w,0.0001);
  var v=c.velocity.xyz;
  v.y=v.y-params.gravity*dt;
  var p=c.position.xyz+v*dt;
  if(p.y<params.groundY){
    p.y=params.groundY;
    if(v.y<0.0){v.y=-v.y*clamp(params.restitution,0.0,1.0);}
    let tangent=vec2<f32>(v.x,v.z);
    let speed=length(tangent);
    let impulse=min(speed,max(params.friction,0.0)*dt*params.gravity);
    if(speed>1e-7){
      let damped=tangent*((speed-impulse)/speed);
      v.x=damped.x; v.z=damped.y;
    }
  }
  let stress=clamp(c.state.y,0.0,1.0);
  c.state.x=max(0.0,c.state.x-max(params.energyDrain,0.0)*stress*dt/mass);
  c.velocity=vec4<f32>(v,clamp(c.velocity.w,0.0,1.0));
  c.position=vec4<f32>(p,mass);
  cells[i]=c;
}\`;
function align(n,a){return Math.ceil(n/a)*a;}

export class SomaticGPU {
  static async create({cellCount=4096,seed=1,gravity=9.81,groundY=0,
    restitution=0.05,friction=4,energyDrain=0.02,pageBytes=16*1024*1024}={}) {
    if(!Number.isSafeInteger(cellCount)||cellCount<1)throw new RangeError("cellCount must be positive");
    if(!navigator.gpu)throw new Error("WebGPU unavailable");
    const adapter=await navigator.gpu.requestAdapter();
    if(!adapter)throw new Error("No WebGPU adapter");
    const pageLimit=Math.min(pageBytes,adapter.limits.maxStorageBufferBindingSize,adapter.limits.maxBufferSize);
    const cellsPerPage=Math.floor(pageLimit/CELL_BYTES);
    if(cellsPerPage<1)throw new Error("GPU buffer limit cannot hold one cell");
    const device=await adapter.requestDevice();
    const module=device.createShaderModule({label:"Somatic 48-byte integrator",code:WGSL});
    const compilation=await module.getCompilationInfo();
    const errors=compilation.messages.filter(m=>m.type==="error");
    if(errors.length){device.destroy();throw new Error(errors.map(e=>e.message).join("\\n"));}
    const pipeline=await device.createComputePipelineAsync({layout:"auto",compute:{module,entryPoint:"main"}});
    let rngState=seed>>>0||1;
    const random=()=>{rngState^=rngState<<13;rngState^=rngState>>>17;rngState^=rngState<<5;return(rngState>>>0)/4294967296;};
    const pages=[];let remaining=cellCount,offset=0;
    while(remaining>0){
      const count=Math.min(remaining,cellsPerPage),floats=new Float32Array(count*FLOATS_PER_CELL);
      for(let i=0;i<count;i++){
        const o=i*12;
        floats[o]=(random()-.5)*2;floats[o+1]=.25+random()*2;floats[o+2]=(random()-.5)*2;floats[o+3]=.5+random();
        floats[o+4]=0;floats[o+5]=0;floats[o+6]=0;floats[o+7]=.8;
        floats[o+8]=1;floats[o+9]=random()*.1;floats[o+10]=1.61803398875;floats[o+11]=random();
      }
      const bytes=count*CELL_BYTES;
      const buffer=device.createBuffer({label:"Somatic cells "+offset,size:align(bytes,4),usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC|GPUBufferUsage.COPY_DST});
      device.queue.writeBuffer(buffer,0,floats);
      const uniform=device.createBuffer({label:"Somatic parameters",size:32,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
      const bindGroup=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[
        {binding:0,resource:{buffer,size:bytes}},{binding:1,resource:{buffer:uniform}}
      ]});
      pages.push({buffer,uniform,bindGroup,count,offset});offset+=count;remaining-=count;
    }
    return new SomaticGPU({device,pipeline,pages,cellCount,gravity,groundY,restitution,friction,energyDrain});
  }
  constructor(options){Object.assign(this,options);this.disposed=false;this.steps=0;this.simulationTime=0;}
  step(deltaSeconds){
    if(this.disposed)throw new Error("SomaticGPU disposed");
    if(!Number.isFinite(deltaSeconds)||deltaSeconds<0)throw new RangeError("deltaSeconds must be finite and non-negative");
    const dt=Math.min(deltaSeconds,MAX_DT),encoder=this.device.createCommandEncoder({label:"Somatic step"});
    const pass=encoder.beginComputePass();pass.setPipeline(this.pipeline);
    for(const page of this.pages){
      const data=new ArrayBuffer(32),f=new Float32Array(data),u=new Uint32Array(data);
      f[0]=dt;f[1]=this.gravity;f[2]=this.groundY;f[3]=this.restitution;f[4]=this.friction;f[5]=this.energyDrain;u[6]=page.count;u[7]=0;
      this.device.queue.writeBuffer(page.uniform,0,data);
      pass.setBindGroup(0,page.bindGroup);pass.dispatchWorkgroups(Math.ceil(page.count/WORKGROUP_SIZE));
    }
    pass.end();this.device.queue.submit([encoder.finish()]);
    this.steps++;this.simulationTime+=dt;
    return{steps:this.steps,simulationTime:this.simulationTime,delta:dt,cells:this.cellCount,pages:this.pages.length};
  }
  async readback(){
    if(this.disposed)throw new Error("SomaticGPU disposed");
    await this.device.queue.onSubmittedWorkDone();
    const result=new Float32Array(this.cellCount*FLOATS_PER_CELL);
    for(const page of this.pages){
      const size=page.count*CELL_BYTES,staging=this.device.createBuffer({size,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
      const encoder=this.device.createCommandEncoder();encoder.copyBufferToBuffer(page.buffer,0,staging,0,size);this.device.queue.submit([encoder.finish()]);
      await staging.mapAsync(GPUMapMode.READ);
      result.set(new Float32Array(staging.getMappedRange().slice(0)),page.offset*FLOATS_PER_CELL);
      staging.unmap();staging.destroy();
    }
    return result;
  }
  dispose(){
    if(this.disposed)return;
    for(const p of this.pages){p.buffer.destroy();p.uniform.destroy();}
    this.device.destroy();this.disposed=true;
  }
}
export {CELL_BYTES,FLOATS_PER_CELL,WGSL as SOMATIC_WGSL};
