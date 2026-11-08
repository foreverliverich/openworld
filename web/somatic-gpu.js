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
  friction: f32, energyDrain: f32, cellCount: u32, baseCell: u32,
  attractionCenter: vec4<f32>,
  attractionStrength: f32, maxAttractionAcceleration: f32, _pad2: vec2<f32>,
  audioBands: vec4<f32>, audioCenter: vec4<f32>,
  audioStrength: f32, audioSpatialScale: f32, audioPhase: f32, _pad3: f32,
};
@group(0) @binding(0) var<storage, read_write> cells: array<SomaticCell>;
@group(0) @binding(1) var<uniform> params: SimParams;
@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
  let i=gid.x+params.baseCell;
  if(gid.x>=params.cellCount || i>=arrayLength(&cells)){return;}
  var c=cells[i];
  let dt=clamp(params.dt,0.0,0.0333333333);
  let mass=max(c.position.w,0.0001);
  var v=c.velocity.xyz;
  // Optional bounded goal steering. A zero-distance guard prevents NaNs.
  let toGoal=params.attractionCenter.xyz-c.position.xyz;
  let goalDistance=length(toGoal);
  if(params.attractionStrength>0.0 && goalDistance>1e-5){
    let acceleration=min(params.attractionStrength*goalDistance,
                         max(params.maxAttractionAcceleration,0.0));
    v=v+(toGoal/goalDistance)*acceleration*dt;
  }
  // Spectral bands drive bounded, distinct body forces: bass vertically,
  // mids radially, highs tangentially. This is a controllable ripple force,
  // not a claim that the body reproduces acoustic pressure or resonance.
  let audioOffset=c.position.xyz-params.audioCenter.xyz;
  let audioRadius=length(audioOffset);
  if(params.audioStrength>0.0 && audioRadius>1e-5){
    let radial=audioOffset/audioRadius;
    let tangent=vec3<f32>(-radial.z,0.0,radial.x);
    let wave=sin(audioRadius*params.audioSpatialScale-params.audioPhase);
    let bands=clamp(params.audioBands.xyz,vec3<f32>(0.0),vec3<f32>(1.0));
    let audioForce=vec3<f32>(
      radial.x*bands.y+tangent.x*bands.z,
      bands.x,
      radial.z*bands.y+tangent.z*bands.z
    )*wave*clamp(params.audioStrength,0.0,20.0);
    v=v+audioForce*dt;
  }
  v.y=v.y-params.gravity*dt;
  var p=c.position.xyz+v*dt;
  if(p.y<params.groundY){
    p.y=params.groundY;
    if(v.y<0.0){v.y=-v.y*clamp(params.restitution,0.0,1.0);}
    let tangent=vec2<f32>(v.x,v.z);
    let speed=length(tangent);
    let frictionImpulse=min(speed,max(params.friction,0.0)*dt*params.gravity);
    if(speed>1e-7){
      let damped=tangent*((speed-frictionImpulse)/speed);
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
    restitution=0.05,friction=4,energyDrain=0.02,pageBytes=16*1024*1024,
    rotationFrames=5,maxCellsPerFrame=262144}={}) {
    if(!Number.isSafeInteger(cellCount)||cellCount<1)throw new RangeError("cellCount must be positive");
    if(!Number.isSafeInteger(rotationFrames)||rotationFrames<1)throw new RangeError("rotationFrames must be a positive integer");
    if(!Number.isSafeInteger(maxCellsPerFrame)||maxCellsPerFrame<1)throw new RangeError("maxCellsPerFrame must be a positive integer");
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
      const uniform=device.createBuffer({label:"Somatic parameters",size:112,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
      const bindGroup=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[
        {binding:0,resource:{buffer,size:bytes}},{binding:1,resource:{buffer:uniform}}
      ]});
      pages.push({buffer,uniform,bindGroup,count,offset});offset+=count;remaining-=count;
    }
    return new SomaticGPU({device,pipeline,pages,cellCount,gravity,groundY,restitution,friction,energyDrain,
      rotationFrames,maxCellsPerFrame,cursor:0,
      attractionCenter:[0,0,0],attractionStrength:0,maxAttractionAcceleration:8,
      audioBands:[0,0,0],audioCenter:[0,0,0],audioStrength:0,audioSpatialScale:2,audioPhase:0});
  }
  constructor(options){Object.assign(this,options);this.disposed=false;this.steps=0;this.simulationTime=0;}
  setAttractor(x,y,z,{strength=1,maxAcceleration=8}={}){
    if(this.disposed)throw new Error("SomaticGPU disposed");
    if(![x,y,z,strength,maxAcceleration].every(Number.isFinite))throw new TypeError("Attractor values must be finite");
    if(strength<0||maxAcceleration<0)throw new RangeError("Attractor strength and acceleration must be non-negative");
    this.attractionCenter=[x,y,z];
    this.attractionStrength=strength;
    this.maxAttractionAcceleration=maxAcceleration;
  }
  clearAttractor(){this.setAttractor(0,0,0,{strength:0,maxAcceleration:this.maxAttractionAcceleration});}
  setAudioDrive(bass,mid,treble,{strength=0,spatialScale=2,phase=0,center=[0,0,0]}={}){
    if(this.disposed)throw new Error("SomaticGPU disposed");
    if(![bass,mid,treble,strength,spatialScale,phase,...center].every(Number.isFinite))
      throw new TypeError("Audio drive values must be finite");
    if(center.length!==3 || strength<0 || strength>20 || spatialScale<=0 || spatialScale>100)
      throw new RangeError("Audio drive is outside its bounded range");
    this.audioBands=[Math.min(1,Math.max(0,bass)),Math.min(1,Math.max(0,mid)),Math.min(1,Math.max(0,treble))];
    this.audioStrength=strength;this.audioSpatialScale=spatialScale;this.audioPhase=phase;
    this.audioCenter=[center[0],center[1],center[2]];
  }
  clearAudioDrive(){this.setAudioDrive(0,0,0,{strength:0,spatialScale:this.audioSpatialScale,phase:0,center:this.audioCenter});}
  step(deltaSeconds){
    if(this.disposed)throw new Error("SomaticGPU disposed");
    if(!Number.isFinite(deltaSeconds)||deltaSeconds<0)throw new RangeError("deltaSeconds must be finite and non-negative");
    const dt=Math.min(deltaSeconds,MAX_DT);
    // Rotate through a bounded slice of the global cell array each frame.
    // The five-frame target is further capped to protect the GPU watchdog.
    const targetChunk=Math.ceil(this.cellCount/this.rotationFrames);
    const budget=Math.min(targetChunk,this.maxCellsPerFrame,this.cellCount-this.cursor);
    let remaining=budget,globalStart=this.cursor,dispatches=0;
    const encoder=this.device.createCommandEncoder({label:"Somatic bounded rotating step"});
    const pass=encoder.beginComputePass();pass.setPipeline(this.pipeline);
    while(remaining>0){
      const page=this.pages.find(p=>globalStart>=p.offset && globalStart<p.offset+p.count);
      if(!page)throw new Error("Somatic page map is incomplete");
      const localStart=globalStart-page.offset;
      const segment=Math.min(remaining,page.count-localStart);
      const data=new ArrayBuffer(112),f=new Float32Array(data),u=new Uint32Array(data);
      f[0]=dt;f[1]=this.gravity;f[2]=this.groundY;f[3]=this.restitution;f[4]=this.friction;f[5]=this.energyDrain;
      u[6]=segment;u[7]=localStart;
      f[8]=this.attractionCenter[0];f[9]=this.attractionCenter[1];f[10]=this.attractionCenter[2];f[11]=0;
      f[12]=this.attractionStrength;f[13]=this.maxAttractionAcceleration;f[14]=0;f[15]=0;
      f[16]=this.audioBands[0];f[17]=this.audioBands[1];f[18]=this.audioBands[2];f[19]=0;
      f[20]=this.audioCenter[0];f[21]=this.audioCenter[1];f[22]=this.audioCenter[2];f[23]=0;
      f[24]=this.audioStrength;f[25]=this.audioSpatialScale;f[26]=this.audioPhase;f[27]=0;
      this.device.queue.writeBuffer(page.uniform,0,data);
      pass.setBindGroup(0,page.bindGroup);
      pass.dispatchWorkgroups(Math.ceil(segment/WORKGROUP_SIZE));
      dispatches++;remaining-=segment;globalStart=globalStart+segment;
    }
    pass.end();this.device.queue.submit([encoder.finish()]);
    this.cursor+=budget;if(this.cursor>=this.cellCount)this.cursor=0;
    this.steps++;this.simulationTime+=dt;
    return{steps:this.steps,simulationTime:this.simulationTime,delta:dt,cells:this.cellCount,
      processedCells:budget,dispatches,cursor:this.cursor,rotationFrames:this.rotationFrames};
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
