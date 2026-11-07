const FORM = Object.freeze({ humanoid: 0, quadruped: 1, insect: 2, custom: 3 });

const vertexShader = `precision highp float;
in vec3 position;
out vec3 vLocalPosition;
void main() {
  vLocalPosition = position;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;

const fragmentShader = `precision highp float;
in vec3 vLocalPosition;
out vec4 outColor;
uniform vec3 uCameraLocal;
uniform float uFromForm;
uniform float uToForm;
uniform float uMorph;
uniform float uSimulationTime;

float sdSphere(vec3 p, float r) { return length(p) - r; }
float sdEllipsoid(vec3 p, vec3 r) {
  float k0 = length(p / r);
  float k1 = length(p / (r * r));
  return k0 * (k0 - 1.0) / max(k1, 1e-5);
}
float sdCapsule(vec3 p, vec3 a, vec3 b, float r) {
  vec3 pa = p-a, ba = b-a;
  float h = clamp(dot(pa,ba)/dot(ba,ba),0.0,1.0);
  return length(pa-ba*h)-r;
}
float smin(float a, float b, float k) {
  float h = clamp(0.5+0.5*(b-a)/k,0.0,1.0);
  return mix(b,a,h)-k*h*(1.0-h);
}
float hash13(vec3 p) {
  p = fract(p * 0.1031);
  p += dot(p, p.yzx + 33.33);
  return fract((p.x+p.y)*p.z);
}
float noise3(vec3 x) {
  vec3 i=floor(x), f=fract(x);
  f=f*f*(3.0-2.0*f);
  return mix(mix(mix(hash13(i),hash13(i+vec3(1,0,0)),f.x),
                 mix(hash13(i+vec3(0,1,0)),hash13(i+vec3(1,1,0)),f.x),f.y),
             mix(mix(hash13(i+vec3(0,0,1)),hash13(i+vec3(1,0,1)),f.x),
                 mix(hash13(i+vec3(0,1,1)),hash13(i+vec3(1,1,1)),f.x),f.y),f.z);
}
float fbm(vec3 p) {
  float v=0.0, a=0.5;
  mat3 r=mat3(0.00,0.80,0.60,-0.80,0.36,-0.48,-0.60,-0.48,0.64);
  for(int i=0;i<4;i++){v+=a*noise3(p);p=r*p*2.03+7.1;a*=0.5;}
  return v;
}
vec3 opLatentWarp(vec3 p, float strength) {
  vec3 q=p;
  q.x += strength*(fbm(p*2.7)-0.5);
  q.y += strength*(fbm(p.yzx*3.1+4.7)-0.5);
  q.z += strength*(fbm(p.zxy*2.9+9.2)-0.5);
  return q;
}

float humanoid(vec3 p) {
  float d=sdEllipsoid(p-vec3(0.0,-0.05,0.0),vec3(0.30,0.40,0.205));
  d=smin(d,sdEllipsoid(p-vec3(0.0,0.61,0.0),vec3(0.175,0.205,0.17)),0.13);
  d=smin(d,sdCapsule(p,vec3(0,0.34,0),vec3(0,0.48,0),0.095),0.09);
  d=smin(d,sdCapsule(p,vec3(-0.25,0.22,0),vec3(-0.40,-0.24,0),0.078),0.075);
  d=smin(d,sdCapsule(p,vec3(0.25,0.22,0),vec3(0.40,-0.24,0),0.078),0.075);
  d=smin(d,sdCapsule(p,vec3(-0.145,-0.34,0),vec3(-0.17,-0.88,0),0.105),0.08);
  d=smin(d,sdCapsule(p,vec3(0.145,-0.34,0),vec3(0.17,-0.88,0),0.105),0.08);
  d=smin(d,sdEllipsoid(p-vec3(-0.17,-0.90,0.055),vec3(0.13,0.07,0.20)),0.055);
  d=smin(d,sdEllipsoid(p-vec3(0.17,-0.90,0.055),vec3(0.13,0.07,0.20)),0.055);
  return d;
}
float quadruped(vec3 p) {
  float d=sdEllipsoid(p-vec3(0.0,0.12,0.0),vec3(0.72,0.30,0.29));
  d=smin(d,sdCapsule(p,vec3(0.43,0.18,0),vec3(0.70,0.36,0),0.16),0.12);
  d=smin(d,sdEllipsoid(p-vec3(0.77,0.38,0),vec3(0.22,0.19,0.19)),0.12);
  d=smin(d,sdEllipsoid(p-vec3(0.91,0.31,0),vec3(0.19,0.09,0.14)),0.08);
  d=smin(d,sdCapsule(p,vec3(-0.62,0.18,0),vec3(-0.98,0.43,0),0.045),0.035);
  for(int side=-1;side<=1;side+=2){
    for(int zside=-1;zside<=1;zside+=2){
      float x=float(side)*0.43, z=float(zside)*0.19;
      d=smin(d,sdCapsule(p,vec3(x,0.0,z),vec3(x+float(side)*0.035,-0.78,z),0.075),0.06);
      d=smin(d,sdEllipsoid(p-vec3(x+float(side)*0.035,-0.79,z+0.025),vec3(0.105,0.055,0.095)),0.04);
    }
  }
  return d;
}
float insect(vec3 p) {
  float d=sdEllipsoid(p-vec3(0.0,0.02,0.0),vec3(0.25,0.31,0.20));
  d=smin(d,sdEllipsoid(p-vec3(0.0,-0.39,0.0),vec3(0.31,0.30,0.22)),0.10);
  d=smin(d,sdEllipsoid(p-vec3(0.0,0.49,0.0),vec3(0.19,0.17,0.17)),0.09);
  for(int side=-1;side<=1;side+=2){
    for(int row=0;row<3;row++){
      float y=0.12-float(row)*0.19;
      vec3 a=vec3(float(side)*0.17,y,0.0);
      vec3 b=vec3(float(side)*(0.48+0.04*float(row)),y-0.22,0.0);
      vec3 c=vec3(float(side)*(0.56+0.04*float(row)),y-0.58,0.035);
      d=smin(d,sdCapsule(p,a,b,0.035),0.025);
      d=smin(d,sdCapsule(p,b,c,0.027),0.02);
    }
    d=smin(d,sdCapsule(p,vec3(float(side)*0.07,0.61,0),vec3(float(side)*0.17,0.91,0.015),0.018),0.012);
  }
  return d;
}
float formDistance(vec3 p, float form) {
  if(form<0.5) return humanoid(p);
  if(form<1.5) return quadruped(p);
  if(form<2.5) return insect(p);
  return humanoid(p);
}
float mapBody(vec3 p) {
  vec3 warped=opLatentWarp(p,0.008);
  float a=formDistance(warped,uFromForm);
  float b=formDistance(warped,uToForm);
  float d=mix(a,b,clamp(uMorph,0.0,1.0));
  return d;
}
vec3 calcNormal(vec3 p) {
  const float e=0.0015;
  return normalize(vec3(
    mapBody(p+vec3(e,0,0))-mapBody(p-vec3(e,0,0)),
    mapBody(p+vec3(0,e,0))-mapBody(p-vec3(0,e,0)),
    mapBody(p+vec3(0,0,e))-mapBody(p-vec3(0,0,e))
  ));
}
void main() {
  vec3 rd=normalize(vLocalPosition-uCameraLocal);
  float t=length(vLocalPosition-uCameraLocal);
  float hit=0.0;
  vec3 p=uCameraLocal+rd*t;
  for(int i=0;i<112;i++){
    p=uCameraLocal+rd*t;
    float d=mapBody(p);
    if(d<0.0018){hit=1.0;break;}
    t+=max(d*0.72,0.0015);
    if(t>8.0) break;
  }
  if(hit<0.5) discard;
  vec3 n=calcNormal(p);
  vec3 lightDir=normalize(vec3(-0.45,0.75,0.55));
  float ndl=max(dot(n,lightDir),0.0);
  float wrap=max((dot(n,lightDir)+0.42)/1.42,0.0);
  float pores=fbm(p*115.0);
  float flow=fbm(p*5.0+vec3(0.0,uSimulationTime*0.015,0.0));
  vec3 skin=mix(vec3(0.20,0.37,0.34),vec3(0.48,0.66,0.57),0.5+0.5*flow);
  skin*=0.96+0.07*pores;
  vec3 color=skin*(0.22+0.72*ndl)+vec3(0.22,0.10,0.075)*wrap*0.32;
  color+=vec3(0.08,0.19,0.16)*pow(1.0-max(dot(n,normalize(uCameraLocal-p)),0.0),3.0)*0.22;
  vec4 clip=projectionMatrix*modelViewMatrix*vec4(p,1.0);
  gl_FragDepth=clip.z/clip.w*0.5+0.5;
  outColor=vec4(color,1.0);
}`;

function formCode(name) { return FORM[name] ?? FORM.humanoid; }

export function createSdfBodyMesh(THREE, entity) {
  const model=entity.metadata?.body_model;
  if(!model || model.schema_version!==1 || model.representation!=="analytic_sdf") {
    throw new Error("Body prototype is missing a supported analytic SDF model");
  }
  const uniforms={
    uCameraLocal:{value:new THREE.Vector3()},
    uFromForm:{value:formCode(model.from_form)},
    uToForm:{value:formCode(model.to_form)},
    uMorph:{value:0},
    uSimulationTime:{value:0}
  };
  const material=new THREE.ShaderMaterial({
    glslVersion:THREE.GLSL3,
    uniforms,
    vertexShader,
    fragmentShader,
    side:THREE.FrontSide,
    depthTest:true,
    depthWrite:true
  });
  const mesh=new THREE.Mesh(new THREE.SphereGeometry(1.38,48,32),material);
  mesh.scale.set(entity.size.x/2,entity.size.y/2,entity.size.z/2);
  mesh.position.set(entity.position.x,entity.position.y,entity.position.z);
  mesh.userData.entityId=entity.entity_id;
  mesh.userData.bodyModel=model;
  mesh.userData.simulationTime=0;
  mesh.onBeforeRender=(_renderer,_scene,camera)=>{
    mesh.updateMatrixWorld();
    uniforms.uCameraLocal.value.copy(camera.position);
    mesh.worldToLocal(uniforms.uCameraLocal.value);
  };
  return mesh;
}

export function updateSdfBodyMesh(mesh, entity, simulationTime) {
  const model=entity.metadata?.body_model;
  if(!model || model.schema_version!==1) return;
  mesh.position.set(entity.position.x,entity.position.y,entity.position.z);
  mesh.scale.set(entity.size.x/2,entity.size.y/2,entity.size.z/2);
  mesh.userData.bodyModel=model;
  mesh.userData.simulationTime=simulationTime;
  const elapsed=Math.max(0,simulationTime-model.morph_start_simulation_time);
  const progress=Math.max(0,Math.min(1,elapsed/model.morph_duration));
  mesh.material.uniforms.uFromForm.value=formCode(model.from_form);
  mesh.material.uniforms.uToForm.value=formCode(model.to_form);
  mesh.material.uniforms.uMorph.value=progress;
  mesh.material.uniforms.uSimulationTime.value=simulationTime;
}
