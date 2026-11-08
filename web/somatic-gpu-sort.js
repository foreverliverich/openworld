/* GPU-resident, four-bit LSD radix sorter for SomaticCell pages.
 * Ordering: far-to-near camera-space depth. Equal-depth ordering is not stable.
 * No per-frame readback. The returned index buffer is consumed by a future
 * indexed/indirect splat renderer; this module does not draw splats.
 */
const WG=256, RADIX=16, PASSES=8;
const DEPTH_WGSL=String.raw\`
struct SomaticCell { position: vec4<f32>, velocity: vec4<f32>, state: vec4<f32>, };
struct DepthParams { view: mat4x4<f32>, count: u32, baseIndex: u32, _pad: vec2<u32>, };
@group(0) @binding(0) var<storage, read> cells: array<SomaticCell>;
@group(0) @binding(1) var<storage, read_write> keys: array<u32>;
@group(0) @binding(2) var<storage, read_write> values: array<u32>;
@group(0) @binding(3) var<uniform> params: DepthParams;
@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
  if(gid.x>=params.count){return;}
  let index=params.baseIndex+gid.x;
  if(index>=arrayLength(&keys)||index>=arrayLength(&values)){return;}
  let viewPosition=params.view*vec4<f32>(cells[gid.x].position.xyz,1.0);
  let depth=-viewPosition.z;
  var key=0u;
  if(depth>=0.0 && depth<=3.402823e+38){key=~bitcast<u32>(depth);}
  keys[index]=key;values[index]=index;
}\`;
const HIST_WGSL=String.raw\`
struct Params { count:u32, groupCount:u32, bitShift:u32, _pad:u32, };
@group(0) @binding(0) var<storage, read> keys:array<u32>;
@group(0) @binding(1) var<storage, read_write> histogram:array<u32>;
@group(0) @binding(2) var<uniform> params:Params;
var<workgroup> bins:array<atomic<u32>,16>;
@compute @workgroup_size(256)
fn main(@builtin(workgroup_id) wid:vec3<u32>,@builtin(local_invocation_index) lid:u32){
  if(lid<16u){atomicStore(&bins[lid],0u);} workgroupBarrier();
  let i=wid.x*256u+lid;
  if(i<params.count){let b=(keys[i]>>params.bitShift)&15u;atomicAdd(&bins[b],1u);}
  workgroupBarrier();
  if(lid<16u){histogram[wid.x*16u+lid]=atomicLoad(&bins[lid]);}
}\`;
const PREFIX_WGSL=String.raw\`
struct Params { count:u32, groupCount:u32, bitShift:u32, _pad:u32, };
@group(0) @binding(0) var<storage, read> histogram:array<u32>;
@group(0) @binding(1) var<storage, read_write> offsets:array<u32>;
@group(0) @binding(2) var<uniform> params:Params;
@compute @workgroup_size(16)
fn main(@builtin(global_invocation_id) gid:vec3<u32>){
  let bucket=gid.x;if(bucket>=16u){return;}
  var bucketBase=0u;
  for(var lower=0u;lower<bucket;lower++){
    for(var g=0u;g<params.groupCount;g++){bucketBase+=histogram[g*16u+lower];}
  }
  var running=bucketBase;
  for(var g=0u;g<params.groupCount;g++){
    let slot=g*16u+bucket;offsets[slot]=running;running+=histogram[slot];
  }
}\`;
const SCATTER_WGSL=String.raw\`
struct Params { count:u32, groupCount:u32, bitShift:u32, _pad:u32, };
@group(0) @binding(0) var<storage, read> keysIn:array<u32>;
@group(0) @binding(1) var<storage, read> valuesIn:array<u32>;
@group(0) @binding(2) var<storage, read_write> keysOut:array<u32>;
@group(0) @binding(3) var<storage, read_write> valuesOut:array<u32>;
@group(0) @binding(4) var<storage, read> offsets:array<u32>;
@group(0) @binding(5) var<uniform> params:Params;
var<workgroup> bins:array<atomic<u32>,16>;
@compute @workgroup_size(256)
fn main(@builtin(workgroup_id) wid:vec3<u32>,@builtin(local_invocation_index) lid:u32){
  if(lid<16u){atomicStore(&bins[lid],0u);}workgroupBarrier();
  let i=wid.x*256u+lid;
  var bucket=0u;var localRank=0u;
  if(i<params.count){
    let key=keysIn[i];bucket=(key>>params.bitShift)&15u;
    localRank=atomicAdd(&bins[bucket],1u);
  }
  workgroupBarrier();
  if(i<params.count){
    let destination=offsets[wid.x*16u+bucket]+localRank;
    keysOut[destination]=keysIn[i];valuesOut[destination]=valuesIn[i];
  }
}\`;

function makeBuffer(device,label,size,extra=0){
  if(!Number.isSafeInteger(size)||size<4)throw new RangeError("Invalid GPU buffer size: "+label);
  return device.createBuffer({label,size:Math.ceil(size/4)*4,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC|GPUBufferUsage.COPY_DST|extra});
}
function checkedView(view){
  const a=view instanceof Float32Array?view:new Float32Array(view);
  if(a.length!==16||!Array.from(a).every(Number.isFinite))throw new TypeError("viewMatrix must contain 16 finite floats");
  return a;
}
export class SomaticRadixSorter {
  static async create({device,pages,cellCount,maxStorageBufferBindingSize=device?.limits?.maxStorageBufferBindingSize}={}){
    if(!device||!Array.isArray(pages)||!pages.length)throw new TypeError("device and non-empty Somatic pages are required");
    if(!Number.isSafeInteger(cellCount)||cellCount<1)throw new RangeError("cellCount must be positive");
    const bytes=cellCount*4,groupCount=Math.ceil(cellCount/WG),scratchBytes=groupCount*RADIX*4;
    if(bytes>maxStorageBufferBindingSize||scratchBytes>maxStorageBufferBindingSize)
      throw new RangeError("Radix buffers exceed maxStorageBufferBindingSize; use a hierarchical multi-level sorter");
    let expected=0;
    for(const p of pages){if(p.offset!==expected||!Number.isSafeInteger(p.count)||p.count<1||!p.buffer)throw new Error("Somatic pages must be contiguous and ordered");expected+=p.count;}
    if(expected!==cellCount)throw new Error("Somatic page count does not match cellCount");
    const modules=[DEPTH_WGSL,HIST_WGSL,PREFIX_WGSL,SCATTER_WGSL].map((code,i)=>device.createShaderModule({label:["Somatic depth keys","Somatic radix histogram","Somatic radix prefix","Somatic radix scatter"][i],code}));
    for(const m of modules){const info=await m.getCompilationInfo();const errors=info.messages.filter(x=>x.type==="error");if(errors.length)throw new Error(errors.map(x=>x.message).join("\\n"));}
    const pipelines=await Promise.all(modules.map((module,i)=>device.createComputePipelineAsync({layout:"auto",compute:{module,entryPoint:"main"}})));
    const [depthPipeline,histPipeline,prefixPipeline,scatterPipeline]=pipelines;
    const keysA=makeBuffer(device,"Somatic radix keys A",bytes);
    const keysB=makeBuffer(device,"Somatic radix keys B",bytes);
    const valuesA=makeBuffer(device,"Somatic radix indices A",bytes);
    const valuesB=makeBuffer(device,"Somatic radix indices B",bytes);
    const histogram=makeBuffer(device,"Somatic radix histogram",scratchBytes);
    const offsets=makeBuffer(device,"Somatic radix offsets",scratchBytes);
    const depthGroups=pages.map(p=>{
      const uniform=device.createBuffer({label:"Somatic depth camera/page params",size:80,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
      const bindGroup=device.createBindGroup({layout:depthPipeline.getBindGroupLayout(0),entries:[
        {binding:0,resource:{buffer:p.buffer,size:p.count*48}},
        {binding:1,resource:{buffer:keysA,size:bytes}},
        {binding:2,resource:{buffer:valuesA,size:bytes}},
        {binding:3,resource:{buffer:uniform}}
      ]});
      return {page:p,uniform,bindGroup};
    });
    const prefixUniform=device.createBuffer({label:"Somatic radix prefix params",size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
    device.queue.writeBuffer(prefixUniform,0,new Uint32Array([cellCount,groupCount,0,0]));
    const prefixGroup=device.createBindGroup({layout:prefixPipeline.getBindGroupLayout(0),entries:[
      {binding:0,resource:{buffer:histogram,size:scratchBytes}},
      {binding:1,resource:{buffer:offsets,size:scratchBytes}},
      {binding:2,resource:{buffer:prefixUniform}}
    ]});
    const rounds=[];
    for(let pass=0;pass<PASSES;pass++){
      const shift=pass*4,uniform=device.createBuffer({label:"Somatic radix pass "+shift,size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
      device.queue.writeBuffer(uniform,0,new Uint32Array([cellCount,groupCount,shift,0]));
      const histGroup=device.createBindGroup({layout:histPipeline.getBindGroupLayout(0),entries:[
        {binding:0,resource:{buffer:pass%2===0?keysA:keysB,size:bytes}},
        {binding:1,resource:{buffer:histogram,size:scratchBytes}},
        {binding:2,resource:{buffer:uniform}}
      ]});
      const scatterGroup=device.createBindGroup({layout:scatterPipeline.getBindGroupLayout(0),entries:[
        {binding:0,resource:{buffer:pass%2===0?keysA:keysB,size:bytes}},
        {binding:1,resource:{buffer:pass%2===0?valuesA:valuesB,size:bytes}},
        {binding:2,resource:{buffer:pass%2===0?keysB:keysA,size:bytes}},
        {binding:3,resource:{buffer:pass%2===0?valuesB:valuesA,size:bytes}},
        {binding:4,resource:{buffer:offsets,size:scratchBytes}},
        {binding:5,resource:{buffer:uniform}}
      ]});
      rounds.push({uniform,histGroup,scatterGroup});
    }
    return new SomaticRadixSorter({device,cellCount,groupCount,depthPipeline,histPipeline,prefixPipeline,scatterPipeline,
      keysA,keysB,valuesA,valuesB,histogram,offsets,depthGroups,prefixGroup,rounds,disposed:false});
  }
  constructor(state){Object.assign(this,state);}
  encode(commandEncoder,viewMatrix){
    if(this.disposed)throw new Error("SomaticRadixSorter disposed");
    const view=checkedView(viewMatrix);
    for(const item of this.depthGroups){
      const data=new ArrayBuffer(80),f=new Float32Array(data),u=new Uint32Array(data);
      f.set(view,0);u[16]=item.page.count;u[17]=item.page.offset;
      this.device.queue.writeBuffer(item.uniform,0,data);
    }
    for(const item of this.depthGroups){
      const pass=commandEncoder.beginComputePass({label:"Somatic camera depth keys"});
      pass.setPipeline(this.depthPipeline);pass.setBindGroup(0,item.bindGroup);
      pass.dispatchWorkgroups(Math.ceil(item.page.count/WG));pass.end();
    }
    for(const round of this.rounds){
      let pass=commandEncoder.beginComputePass({label:"Somatic radix histogram"});
      pass.setPipeline(this.histPipeline);pass.setBindGroup(0,round.histGroup);
      pass.dispatchWorkgroups(this.groupCount);pass.end();
      pass=commandEncoder.beginComputePass({label:"Somatic radix prefix"});
      pass.setPipeline(this.prefixPipeline);pass.setBindGroup(0,this.prefixGroup);
      pass.dispatchWorkgroups(1);pass.end();
      pass=commandEncoder.beginComputePass({label:"Somatic radix scatter"});
      pass.setPipeline(this.scatterPipeline);pass.setBindGroup(0,round.scatterGroup);
      pass.dispatchWorkgroups(this.groupCount);pass.end();
    }
    return this.valuesA;
  }
  sort(viewMatrix){
    if(this.disposed)throw new Error("SomaticRadixSorter disposed");
    const encoder=this.device.createCommandEncoder({label:"Somatic GPU radix sort"});
    const result=this.encode(encoder,viewMatrix);
    this.device.queue.submit([encoder.finish()]);
    return result;
  }
  getSortedIndicesBuffer(){if(this.disposed)throw new Error("SomaticRadixSorter disposed");return this.valuesA;}
  dispose(){
    if(this.disposed)return;
    for(const x of this.depthGroups){x.uniform.destroy();}
    this.prefixUniform.destroy();
    for(const x of this.rounds)x.uniform.destroy();
    for(const b of [this.keysA,this.keysB,this.valuesA,this.valuesB,this.histogram,this.offsets])b.destroy();
    this.disposed=true;
  }
}
export {DEPTH_WGSL as SOMATIC_SORT_DEPTH_WGSL,HIST_WGSL as SOMATIC_RADIX_HISTOGRAM_WGSL,
  PREFIX_WGSL as SOMATIC_RADIX_PREFIX_WGSL,SCATTER_WGSL as SOMATIC_RADIX_SCATTER_WGSL};
