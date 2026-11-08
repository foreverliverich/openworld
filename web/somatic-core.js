/* Somatic Core WebGL2 SDF renderer — no mesh proxies or geometry fallbacks. */
const BIO = `
precision highp float;
#define PI 3.14159265359
float hash13(vec3 p){p=fract(p*.1031);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
vec3 hash33(vec3 p){return vec3(hash13(p),hash13(p+17.17),hash13(p+41.73));}
float noise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);float a=hash13(i),b=hash13(i+vec3(1,0,0)),c=hash13(i+vec3(0,1,0)),d=hash13(i+vec3(1,1,0));float e=hash13(i+vec3(0,0,1)),f1=hash13(i+vec3(1,0,1)),g=hash13(i+vec3(0,1,1)),h=hash13(i+vec3(1,1,1));return mix(mix(mix(a,b,f.x),mix(c,d,f.x),f.y),mix(mix(e,f1,f.x),mix(g,h,f.x),f.y),f.z);}
float fbm(vec3 p){float v=0.,a=.5;mat3 r=mat3(.00,.80,.60,-.80,.36,-.48,-.60,-.48,.64);for(int i=0;i<5;i++){v+=a*noise(p);p=r*p*2.03;a*=.48;}return v;}
float diffusion_noise(vec3 p){return .52*noise(p*1.7)+.27*noise(p*3.4+vec3(7.1,2.3,5.7))+.14*noise(p*6.8+vec3(3.7,9.2,1.4))+.07*noise(p*13.6+vec3(8.2,4.1,6.3));}
vec3 opLatentWarp(vec3 p,float s){return p+s*vec3(diffusion_noise(p+vec3(0,13,7))-.5,diffusion_noise(p+vec3(7,0,13))-.5,diffusion_noise(p+vec3(13,7,0))-.5);}
float opFur(float d,vec3 p,float density,float lengthF){float n=diffusion_noise(p*density);return d-(pow(max(n,0.),5.)*lengthF);}
void opTaper(inout vec3 p,float a){float k=1.+a*clamp(p.y, -1.,1.);p.xz/=max(.2,k);}
void opBulge(inout vec3 p,float a){p.xz*=1.-a*exp(-p.y*p.y*2.);}
void opBend(inout vec3 p,float a){float y=p.y;p.x-=a*y*y;p.z+=a*.25*y*y;}
void opInflate(inout vec3 p,float a){p/=max(.2,1.+a*exp(-dot(p,p)*2.));}
void opAsymmetry(inout vec3 p,float a){p.x+=a*sin(p.y*3.1)*.12;}
void opSymX(inout vec3 p){p.x=abs(p.x);}
vec3 opRepLim(vec3 p,vec3 spacing,vec3 limit){return p-spacing*clamp(round(p/spacing),-limit,limit);}
float smin(float a,float b,float k){float h=max(k-abs(a-b),0.)/k;return min(a,b)-h*h*k*.25;}
float smax(float a,float b,float k){return -smin(-a,-b,k);}
float sdSphere(vec3 p,float r){return length(p)-r;}
float sdEllipsoid(vec3 p,vec3 r){float k0=length(p/r),k1=length(p/(r*r));return k0*(k0-1.)/max(k1,1e-5);}
float sdCapsule(vec3 p,vec3 a,vec3 b,float r){vec3 q=p-a,ba=b-a;float h=clamp(dot(q,ba)/dot(ba,ba),0.,1.);return length(q-ba*h)-r;}
vec2 sdHumanoidBase(vec3 p){float torso=sdEllipsoid(p-vec3(0,-.05,0),vec3(.34,.58,.23));float neck=sdCapsule(p,vec3(0,.42,0),vec3(0,.62,0),.13);float head=sdEllipsoid(p-vec3(0,.82,0),vec3(.23,.28,.22));float d=smin(torso,neck,.12);d=smin(d,head,.1);return vec2(d,1.);}
float getSkinPores(vec3 p){return .5+.5*sin(p.x*180.+noise(p*45.)*3.)*sin(p.y*167.+noise(p*51.)*4.);}
float getSubdermalFlow(vec3 p){return .5+.5*sin(p.x*3.2+p.y*2.1+fbm(p*2.)*2.);}
float getSkinRoughness(vec3 p,vec3 n,float matID){return clamp(.64+getSkinPores(p)*.08, .38,.82);}
vec3 preintegratedSSS(vec3 p,vec3 l,vec3 n,float d){float wrap=max(0.,(dot(n,l)+.35)/1.35);float curvature=clamp(1.-d*4.,0.,1.);float flow=getSubdermalFlow(p);return vec3(1.,.38,.24)*wrap*(.08+.16*curvature)*(.75+.25*flow);}
`;
const VERT = `#version 300 es
in vec2 position; out vec2 vUv; void main(){vUv=position*.5+.5;gl_Position=vec4(position,0.,1.);}`;
const FRAG = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 outColor;
uniform vec2 uResolution; uniform float uTime; uniform float uEvolution;
uniform vec3 uCamera; uniform vec3 uTarget; uniform vec3 uColor; uniform float uRoughness; uniform float uMetallic; uniform float uSSS;
${BIO}
vec2 map_object_A(vec3 p){return sdHumanoidBase(p);}
vec2 map_object_B(vec3 p){return sdHumanoidBase(p);}
vec2 mapScene(vec3 p){vec2 a=map_object_A(p),b=map_object_B(p);return vec2(mix(a.x,b.x,uEvolution),mix(a.y,b.y,uEvolution));}
vec3 normalAt(vec3 p){vec2 e=vec2(.0015,0);return normalize(vec3(mapScene(p+e.xyy).x-mapScene(p-e.xyy).x,mapScene(p+e.yxy).x-mapScene(p-e.yxy).x,mapScene(p+e.yyx).x-mapScene(p-e.yyx).x));}
float ambientOcclusion(vec3 p,vec3 n){float occ=0.,sca=1.;for(int i=1;i<=5;i++){float h=.025*float(i);occ+=(h-mapScene(p+n*h).x)*sca;sca*=.68;}return clamp(1.-occ*2.2,0.,1.);}
void main(){vec2 uv=(vUv-.5)*vec2(uResolution.x/uResolution.y,1.);vec3 forward=normalize(uTarget-uCamera),right=normalize(cross(forward,vec3(0,1,0))),up=cross(right,forward);vec3 rd=normalize(forward+uv.x*right*1.05+uv.y*up*1.05);vec3 ro=uCamera;float t=0.;vec2 hit=vec2(1e4,0.);for(int i=0;i<160;i++){vec3 p=ro+rd*t;hit=mapScene(p);if(hit.x<.0015||t>20.)break;t+=max(hit.x*.78,.001);}vec3 col=vec3(.025,.045,.065);if(t<20.){vec3 p=ro+rd*t,n=normalAt(p),light=normalize(vec3(-.5,.8,.65));float diff=max(dot(n,light),0.);float ao=ambientOcclusion(p,n);vec3 view=normalize(ro-p),halfV=normalize(light+view);float rough=getSkinRoughness(p,n,hit.y);float spec=pow(max(dot(n,halfV),0.),mix(18.,100.,1.-rough));float pores=getSkinPores(p);vec3 base=uColor*(.94+.06*getSubdermalFlow(p));if(hit.y>3.5)base=vec3(.94,.78,.52);else if(hit.y>2.5)base=vec3(.68,.10,.16);else if(hit.y>1.5)base=vec3(.52,.18,.22);base*=.94+pores*.08;vec3 sss=preintegratedSSS(p,light,n,hit.x)*uSSS*(hit.y<1.5?1.:.18);col=base*(.19+diff*.86)*ao+sss+vec3(1.)*spec*(.12+uMetallic*.65);float fog=1.-exp(-t*.025);col=mix(col,vec3(.025,.045,.065),fog);}col=pow(max(col,0.),vec3(.4545));outColor=vec4(col,1.);}`;
function shader(gl,type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){const e=gl.getShaderInfoLog(s);gl.deleteShader(s);throw new Error(e||"Shader compilation failed");}return s;}
function buildProgram(gl,a,b){
const extract=(source)=>{const m=source.match(/^\\s*vec2\\s+map_object\\s*\\(\\s*vec3\\s+(\\w+)\\s*\\)\\s*\\{([\\s\\S]*)\\}\\s*$/);if(!m)throw new Error("SDF must define vec2 map_object(vec3 p) { ... }");return m[2].replace(new RegExp("\\\\b"+m[1]+"\\\\b","g"),"p");};
const fragment=FRAG
.replace("vec2 map_object_A(vec3 p){return sdHumanoidBase(p);}","vec2 map_object_A(vec3 p){"+extract(a)+"}")
.replace("vec2 map_object_B(vec3 p){return sdHumanoidBase(p);}","vec2 map_object_B(vec3 p){"+extract(b)+"}");
const p=gl.createProgram(),vs=shader(gl,gl.VERTEX_SHADER,VERT),fs=shader(gl,gl.FRAGMENT_SHADER,fragment);
gl.attachShader(p,vs);gl.attachShader(p,fs);gl.bindAttribLocation(p,0,"position");gl.linkProgram(p);gl.deleteShader(vs);gl.deleteShader(fs);
if(!gl.getProgramParameter(p,gl.LINK_STATUS)){const e=gl.getProgramInfoLog(p);gl.deleteProgram(p);throw new Error(e||"Program link failed");}
return p;
}
const GENESIS=`vec2 map_object(vec3 p){vec2 h=sdHumanoidBase(p);vec3 q=p-vec3(0.,.35,0.);float armL=sdCapsule(q,vec3(-.28,.12,0.),vec3(-.48,-.35,0.),.095);float armR=sdCapsule(q,vec3(.28,.12,0.),vec3(.48,-.35,0.),.095);float legL=sdCapsule(p,vec3(-.16,-.42,0.),vec3(-.19,-.95,.02),.12);float legR=sdCapsule(p,vec3(.16,-.42,0.),vec3(.19,-.95,.02),.12);float d=smin(h.x,armL,.09);d=smin(d,armR,.09);d=smin(d,legL,.1);d=smin(d,legR,.1);vec3 w=opLatentWarp(p,.012);d=opFur(d,w,2.8,.006);return vec2(d,1.);}`;
export class SomaticRenderer{
constructor(canvas){this.canvas=canvas;this.gl=canvas.getContext("webgl2",{antialias:true,alpha:false});if(!this.gl)throw new Error("WebGL2 is required for Somatic Core.");this.a=GENESIS;this.b=GENESIS;this.evolution=1;this.color=[.72,.43,.34];this.material={roughness:.64,metallic:0,sssIntensity:.9};this.time=0;this.camera=[0,0.35,4.3];this.target=[0,0,0];this.program=null;this.resize=()=>{const d=Math.min(devicePixelRatio||1,2),w=Math.max(1,Math.floor(canvas.clientWidth*d)),h=Math.max(1,Math.floor(canvas.clientHeight*d));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;this.gl.viewport(0,0,w,h);}};new ResizeObserver(this.resize).observe(canvas);this.resize();this.gl.bindBuffer(this.gl.ARRAY_BUFFER,this.gl.createBuffer());this.gl.bufferData(this.gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),this.gl.STATIC_DRAW);this.buffer=this.gl.getParameter(this.gl.ARRAY_BUFFER_BINDING);this.program=buildProgram(this.gl,this.a,this.b);this.start=performance.now();this.frame=this.frame.bind(this);requestAnimationFrame(this.frame);}
prepare(pkg){return buildProgram(this.gl,this.b,pkg.sdfScript);}
discardPrepared(program){if(program)this.gl.deleteProgram(program);}
commitPrepared(program,state){if(this.program)this.gl.deleteProgram(this.program);this.program=program;this.a=state.prevSdfScript;this.b=state.sdfScript;this.evolution=Number.isFinite(state.evolutionProgress)?Math.max(0,Math.min(1,state.evolutionProgress)):0;this.morphStartedAt=Number(state.morph_started_at)||0;this.color=state.color||this.color;this.material=state.material||this.material;}
restore(state){const previous=state.prevSdfScript||GENESIS,current=state.sdfScript||GENESIS,candidate=buildProgram(this.gl,previous,current);if(this.program)this.gl.deleteProgram(this.program);this.program=candidate;this.a=previous;this.b=current;this.evolution=Number.isFinite(state.evolutionProgress)?Math.max(0,Math.min(1,state.evolutionProgress)):1;this.morphStartedAt=Number(state.morph_started_at)||0;this.color=state.color||this.color;this.material=state.material||this.material;}
frame(now){this.resize();this.time=(now-this.start)/1000;if(this.morphStartedAt>0)this.evolution=Math.min(1,Math.max(0,(Date.now()/1000-this.morphStartedAt)*1.5));const gl=this.gl;gl.useProgram(this.program);gl.bindBuffer(gl.ARRAY_BUFFER,this.buffer);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0);const u=(n)=>gl.getUniformLocation(this.program,n);gl.uniform2f(u("uResolution"),this.canvas.width,this.canvas.height);gl.uniform1f(u("uTime"),this.time);gl.uniform1f(u("uEvolution"),this.evolution);gl.uniform3fv(u("uCamera"),this.camera);gl.uniform3fv(u("uTarget"),this.target);gl.uniform3fv(u("uColor"),this.color);gl.uniform1f(u("uRoughness"),this.material.roughness);gl.uniform1f(u("uMetallic"),this.material.metallic);gl.uniform1f(u("uSSS"),this.material.sssIntensity);gl.drawArrays(gl.TRIANGLES,0,3);requestAnimationFrame(this.frame);}
}
export {GENESIS};
