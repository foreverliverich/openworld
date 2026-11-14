"""TEC-Q coupled cell engine: deterministic CPU reference and checkpoint oracle.
The 48-byte SomaticCell ABI remains opaque; evolving state is in versioned sidecars.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from copy import deepcopy
import hashlib, json, math
from typing import Iterable, Optional

class TECQError(ValueError): pass

@dataclass(frozen=True)
class TECQConfig:
    cell_count:int=15000; spacing:float=.08; neighbor_radius:float=.14
    max_neighbors:int=24; dt:float=.002; spring_k:float=18.; damping:float=.22
    torsion_k:float=.35; field_diffusion:float=.08; neural_threshold:float=.62
    neural_refractory_ticks:int=4; topology_interval:int=8
    topology_on:float=.58; topology_off:float=.22
    metabolic_rate:float=.0008; repair_rate:float=.0015; seed:int=7
    def validate(self):
        if not isinstance(self.cell_count,int) or isinstance(self.cell_count,bool) or self.cell_count<2: raise TECQError("cell_count must be an integer >= 2")
        if not isinstance(self.max_neighbors,int) or isinstance(self.max_neighbors,bool) or self.max_neighbors<1: raise TECQError("max_neighbors must be a positive integer")
        if not isinstance(self.topology_interval,int) or isinstance(self.topology_interval,bool) or self.topology_interval<0: raise TECQError("topology_interval must be a non-negative integer")
        if not isinstance(self.neural_refractory_ticks,int) or isinstance(self.neural_refractory_ticks,bool) or self.neural_refractory_ticks<0: raise TECQError("neural_refractory_ticks must be a non-negative integer")
        for k in ("spacing","neighbor_radius","dt","spring_k","damping","torsion_k","field_diffusion","neural_threshold","metabolic_rate","repair_rate"):
            v=float(getattr(self,k))
            if not math.isfinite(v) or v<0: raise TECQError(k+" must be finite and non-negative")
        if min(self.spacing,self.neighbor_radius,self.dt)<=0: raise TECQError("spacing, radius and dt must be positive")
        if not 0<=self.topology_off<self.topology_on<=1: raise TECQError("invalid topology hysteresis")

@dataclass
class Bond:
    a:int; b:int; rest:float; weight:float=.5; active:bool=True; torsion:float=0.

def _norm(v:Iterable[float])->float: return math.sqrt(sum(x*x for x in v))
def _clamp(x:float,lo:float=0.,hi:float=1.)->float: return max(lo,min(hi,x))

class TECQState:
    """Structure-of-arrays state indexed by stable cell id."""
    DOMAINS=("position","velocity","orientation","angular_velocity","energy","stress","memory","cohesion","potential","activation","refractory","swarm_intent","phase","strain","prediction_error","organ_id")
    def __init__(self,positions:list[tuple[float,float,float]],organ_ids:Optional[list[int]]=None):
        n=len(positions); self.position=[list(p) for p in positions]
        self.velocity=[[0.,0.,0.] for _ in range(n)]
        self.orientation=[[0.,0.,0.,1.] for _ in range(n)]
        self.angular_velocity=[[0.,0.,0.] for _ in range(n)]
        self.energy=[.9]*n; self.stress=[.05]*n; self.memory=[0.]*n
        self.cohesion=[.5]*n; self.potential=[0.]*n; self.activation=[0.]*n
        self.refractory=[0]*n; self.swarm_intent=[0.]*n; self.phase=[0.]*n
        self.strain=[0.]*n; self.prediction_error=[0.]*n
        self.organ_id=list(organ_ids) if organ_ids is not None else [0]*n
        if len(self.organ_id)!=n: raise TECQError("organ_ids length mismatch")
        self.tick=0; self.time=0.; self.bonds:dict[tuple[int,int],Bond]={}
        self.adjacency=[[] for _ in range(n)]
        self.validate()
    def validate(self):
        n=self.count
        if n<2: raise TECQError("state must contain at least two cells")
        for name in self.DOMAINS:
            if len(getattr(self,name))!=n: raise TECQError(f"{name} sidecar length mismatch")
        for name,width in (("position",3),("velocity",3),("orientation",4),("angular_velocity",3)):
            for i,row in enumerate(getattr(self,name)):
                if len(row)!=width or any(not math.isfinite(float(v)) for v in row): raise TECQError(f"invalid {name} vector at cell {i}")
        for i,q in enumerate(self.orientation):
            if abs(_norm(q)-1.0)>1e-3: raise TECQError(f"orientation quaternion {i} is not normalized")
        for name in ("energy","stress","memory","cohesion","potential","activation","swarm_intent","strain","prediction_error"):
            for i,v in enumerate(getattr(self,name)):
                if not math.isfinite(float(v)) or not 0.0<=float(v)<=1.0: raise TECQError(f"invalid {name} value at cell {i}")
        for i,v in enumerate(self.phase):
            if not math.isfinite(float(v)) or not 0.0<=float(v)<2.0*math.pi: raise TECQError(f"invalid phase at cell {i}")
        if any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in self.refractory): raise TECQError("refractory counters must be non-negative integers")
        if any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in self.organ_id): raise TECQError("organ_id values must be non-negative integers")
        if self.tick<0 or not math.isfinite(self.time) or self.time<0: raise TECQError("invalid simulation clock")
        for key,b in self.bonds.items():
            if key!=(min(b.a,b.b),max(b.a,b.b)) or b.a==b.b or b.a<0 or b.b>=n: raise TECQError("invalid bond endpoints")
            if not math.isfinite(b.rest) or b.rest<=0 or not math.isfinite(b.weight) or not 0<=b.weight<=1 or not math.isfinite(b.torsion) or b.torsion<0: raise TECQError("invalid bond state")
    @property
    def count(self): return len(self.position)
    def rebuild_adjacency(self):
        self.adjacency=[[] for _ in range(self.count)]
        for key,b in self.bonds.items():
            if b.active:
                a,z=key; self.adjacency[a].append((z,key)); self.adjacency[z].append((a,key))
    def digest(self):
        p={"tick":self.tick,"time":self.time,"bonds":[(k,b.rest,b.weight,b.active,b.torsion) for k,b in sorted(self.bonds.items())]}
        p.update({k:getattr(self,k) for k in self.DOMAINS})
        return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    def checkpoint(self):
        return {"format":"tecq-checkpoint","version":1,"tick":self.tick,"time":self.time,
                "arrays":{k:deepcopy(getattr(self,k)) for k in self.DOMAINS},
                "bonds":[asdict(b) for _,b in sorted(self.bonds.items())],"digest":self.digest()}
    @classmethod
    def from_checkpoint(cls,data):
        if data.get("format")!="tecq-checkpoint" or data.get("version")!=1: raise TECQError("unsupported checkpoint")
        a=data.get("arrays",{})
        if any(k not in a for k in cls.DOMAINS): raise TECQError("checkpoint missing sidecar")
        s=cls(a["position"],a["organ_id"])
        for k in cls.DOMAINS: setattr(s,k,a[k])
        s.tick=int(data["tick"]); s.time=float(data["time"])
        for raw in data.get("bonds",[]):
            b=Bond(**raw); key=(min(b.a,b.b),max(b.a,b.b))
            if key in s.bonds or key[0]==key[1] or key[1]>=s.count or key[0]<0: raise TECQError("invalid checkpoint bond")
            s.bonds[key]=b
        s.rebuild_adjacency()
        s.validate()
        if s.digest()!=data.get("digest"): raise TECQError("checkpoint digest mismatch")
        return s

def lattice_state(config:TECQConfig,organ_count:int=3)->TECQState:
    config.validate()
    if not isinstance(organ_count,int) or isinstance(organ_count,bool) or organ_count<1: raise TECQError("organ_count must be a positive integer")
    n=config.cell_count; side=math.ceil(n**(1/3)); pos=[]
    for i in range(n):
        x=i%side; rem=i//side; y=rem%side; z=rem//side
        pos.append((x*config.spacing,y*config.spacing,z*config.spacing))
    return TECQState(pos,[min(organ_count-1,(i*organ_count)//n) for i in range(n)])

class TECQEngine:
    """Bond mechanics + torsion + fields + nervous dynamics + adaptive swarm."""
    def __init__(self,state:TECQState,config:Optional[TECQConfig]=None):
        self.state=state; self.config=config or TECQConfig(cell_count=state.count)
        self.config.validate()
        if state.count!=self.config.cell_count: raise TECQError("state/config cell count mismatch")
        if not state.bonds: self.rebuild_topology()
    def _buckets(self):
        inv=1./self.config.neighbor_radius; buckets={}
        for i,p in enumerate(self.state.position):
            key=tuple(math.floor(v*inv) for v in p); buckets.setdefault(key,[]).append(i)
        return buckets
    def rebuild_topology(self):
        s,c=self.state,self.config; buckets=self._buckets(); inv=1./c.neighbor_radius; r2=c.neighbor_radius**2
        degree=[0]*s.count; new={}
        for i,p in enumerate(s.position):
            cell=tuple(math.floor(v*inv) for v in p); candidates=[]
            for dx in (-1,0,1):
             for dy in (-1,0,1):
              for dz in (-1,0,1):
               for j in buckets.get((cell[0]+dx,cell[1]+dy,cell[2]+dz),()):
                if j<=i or degree[i]>=c.max_neighbors or degree[j]>=c.max_neighbors: continue
                d2=sum((s.position[j][k]-p[k])**2 for k in range(3))
                if 1e-16<d2<=r2: candidates.append((d2,j))
            for d2,j in sorted(candidates):
                if degree[i]>=c.max_neighbors: break
                if degree[j]>=c.max_neighbors: continue
                key=(i,j); old=s.bonds.get(key)
                new[key]=old if old else Bond(i,j,math.sqrt(d2))
                degree[i]+=1; degree[j]+=1
        s.bonds=new; s.rebuild_adjacency()
    def _adapt_topology(self):
        s,c=self.state,self.config
        for key,b in list(s.bonds.items()):
            a,z=key; d=_norm(s.position[a][k]-s.position[z][k] for k in range(3))
            coherence=1.-min(1.,abs(s.phase[a]-s.phase[z])/math.pi)
            predict=1.-.5*(s.prediction_error[a]+s.prediction_error[z])
            useful=_clamp(.45*coherence+.35*predict+.20*min(s.memory[a],s.memory[z]))
            b.weight=_clamp(.92*b.weight+.08*useful)
            if d>c.neighbor_radius*1.65 or b.weight<c.topology_off: del s.bonds[key]
        # Rebuild spatial candidates, preserving surviving edges and enforcing
        # a hard degree cap on both endpoints.
        existing=s.bonds; degree=[0]*s.count
        for a,z in existing: degree[a]+=1; degree[z]+=1
        buckets=self._buckets(); inv=1./c.neighbor_radius; r2=c.neighbor_radius**2
        for i,p in enumerate(s.position):
            if degree[i]>=c.max_neighbors: continue
            cell=tuple(math.floor(v*inv) for v in p); candidates=[]
            for dx in (-1,0,1):
             for dy in (-1,0,1):
              for dz in (-1,0,1):
               for j in buckets.get((cell[0]+dx,cell[1]+dy,cell[2]+dz),()):
                key=(min(i,j),max(i,j))
                if j<=i or key in existing or degree[j]>=c.max_neighbors: continue
                d2=sum((s.position[j][k]-p[k])**2 for k in range(3))
                if 1e-16<d2<=r2:
                    coh=1.-min(1.,abs(s.phase[i]-s.phase[j])/math.pi)
                    score=.55*coh+.25*(1.-s.prediction_error[i])+.20*s.memory[i]
                    if score>=c.topology_on: candidates.append((d2,j))
            for d2,j in sorted(candidates):
                if degree[i]>=c.max_neighbors: break
                if degree[j]>=c.max_neighbors: continue
                key=(i,j); existing[key]=Bond(i,j,math.sqrt(d2),c.topology_on)
                degree[i]+=1; degree[j]+=1
        s.bonds=existing; s.rebuild_adjacency()
    def step(self,external_drive:Optional[list[float]]=None)->dict:
        s,c,n=self.state,self.config,self.state.count
        drive=external_drive if external_drive is not None else [0.]*n
        if len(drive)!=n or any(not math.isfinite(float(v)) for v in drive): raise TECQError("drive must be finite per cell")
        if c.topology_interval>0 and s.tick>0 and s.tick%c.topology_interval==0: self._adapt_topology()
        s.rebuild_adjacency()
        force=[[0.,0.,0.] for _ in range(n)]; torque=[[0.,0.,0.] for _ in range(n)]
        fd=[[0.,0.,0.,0.] for _ in range(n)]; pd=[0.]*n; nd=[0.]*n; sd=[0.]*n; strain=[0.]*n
        for key,b in s.bonds.items():
            if not b.active: continue
            a,z=key; delta=[s.position[z][k]-s.position[a][k] for k in range(3)]
            dist=max(1e-9,_norm(delta)); direction=[v/dist for v in delta]
            ext=dist-b.rest; rel=[s.velocity[z][k]-s.velocity[a][k] for k in range(3)]
            mag=c.spring_k*b.weight*ext+c.damping*sum(rel[k]*direction[k] for k in range(3))
            qa=s.orientation[a]; qb=s.orientation[z]
            rx=-qb[3]*qa[0]+qb[0]*qa[3]-qb[1]*qa[2]+qb[2]*qa[1]
            ry=-qb[3]*qa[1]+qb[0]*qa[2]+qb[1]*qa[3]-qb[2]*qa[0]
            rz=-qb[3]*qa[2]-qb[0]*qa[1]+qb[1]*qa[0]+qb[2]*qa[3]
            rw=qb[3]*qa[3]+qb[0]*qa[0]+qb[1]*qa[1]+qb[2]*qa[2]
            if rw<0: rx,ry,rz,rw=-rx,-ry,-rz,-rw
            relang=[s.angular_velocity[z][k]-s.angular_velocity[a][k] for k in range(3)]
            rotvec=(rx,ry,rz)
            for k in range(3):
                f=mag*direction[k]; force[a][k]+=f; force[z][k]-=f
                t=b.weight*(2.0*c.torsion_k*rotvec[k]+c.damping*relang[k])
                torque[a][k]+=t; torque[z][k]-=t
            b.torsion=2.0*math.atan2(_norm(rotvec),max(1e-9,abs(rw)))
            local=min(1.,abs(ext)/max(b.rest,1e-6))
            strain[a]=max(strain[a],local); strain[z]=max(strain[z],local)
            phase=math.sin(s.phase[z]-s.phase[a]); pd[a]+=phase*b.weight; pd[z]-=phase*b.weight
            for q,arr in enumerate((s.energy,s.stress,s.memory,s.cohesion)):
                flow=c.field_diffusion*b.weight*(arr[z]-arr[a]); fd[a][q]+=flow; fd[z][q]-=flow
            nd[a]+=s.activation[z]*b.weight; nd[z]+=s.activation[a]*b.weight
            sd[a]+=s.swarm_intent[z]*b.weight; sd[z]+=s.swarm_intent[a]*b.weight
        for i in range(n):
            degree=max(1,len(s.adjacency[i])); wsum=sum(s.bonds[key].weight for _,key in s.adjacency[i])
            for k in range(3):
                s.velocity[i][k]+=(force[i][k]-c.damping*s.velocity[i][k])*c.dt
                s.position[i][k]+=s.velocity[i][k]*c.dt
                s.angular_velocity[i][k]+=torque[i][k]*c.dt
            qx,qy,qz,qw=s.orientation[i]; wx,wy,wz=s.angular_velocity[i]; h=.5*c.dt
            q=[qx+h*(wx*qw+wy*qz-wz*qy),qy+h*(-wx*qz+wy*qw+wz*qx),
               qz+h*(wx*qy-wy*qx+wz*qw),qw+h*(-wx*qx-wy*qy-wz*qz)]
            qn=max(1e-12,_norm(q)); s.orientation[i]=[v/qn for v in q]
            pred=abs(drive[i]-s.activation[i]); s.prediction_error[i]=_clamp(.92*s.prediction_error[i]+.08*pred)
            potential=.90*s.potential[i]+.10*drive[i]+.04*nd[i]/degree+.025*s.swarm_intent[i]
            if s.refractory[i]>0:
                s.refractory[i]-=1; s.activation[i]*=.5; potential*=.5
            elif potential>=c.neural_threshold:
                s.activation[i]=1.; s.refractory[i]=c.neural_refractory_ticks; potential=0.
            else: s.activation[i]=_clamp(.88*s.activation[i]+.12*potential)
            s.potential[i]=_clamp(potential)
            consensus=sd[i]/max(1e-9,wsum)
            s.swarm_intent[i]=_clamp(.86*s.swarm_intent[i]+.14*consensus+.12*s.prediction_error[i]-.08*s.stress[i])
            de,ds,dm,dc=fd[i]
            energy=_clamp(s.energy[i]+de-c.metabolic_rate*c.dt*(1.+s.activation[i]))
            stress=_clamp(s.stress[i]+ds+.06*strain[i]+.03*s.prediction_error[i]-.015*(1.-s.activation[i]))
            memory=_clamp(s.memory[i]+dm+.025*s.prediction_error[i]+.012*s.activation[i]-.001*c.dt)
            cohesion=_clamp(s.cohesion[i]+dc+.03*(1.-strain[i])-.02*s.stress[i])
            if energy>.55 and stress<.45: cohesion=_clamp(cohesion+c.repair_rate*c.dt)
            s.energy[i],s.stress[i],s.memory[i],s.cohesion[i]=energy,stress,memory,cohesion
            s.phase[i]=(s.phase[i]+c.dt*(.25+.5*s.swarm_intent[i]+.2*pd[i]))%(2.*math.pi)
            s.strain[i]=strain[i]
        s.tick+=1; s.time+=c.dt
        s.validate()
        return self.metrics()
    def metrics(self):
        s=self.state; n=s.count; mean=lambda x:sum(x)/n
        return {"tick":s.tick,"time":s.time,"cells":n,"bonds":len(s.bonds),
                "mean_energy":mean(s.energy),"mean_stress":mean(s.stress),
                "mean_memory":mean(s.memory),"mean_cohesion":mean(s.cohesion),
                "mean_activation":mean(s.activation),"mean_swarm_intent":mean(s.swarm_intent),
                "mean_prediction_error":mean(s.prediction_error),"max_strain":max(s.strain),
                "state_digest":s.digest()}
    def isce_projection(self):
        s=self.state; n=s.count
        return {"environmental_energy":sum(s.energy)/n,"environmental_stress":sum(s.stress)/n,
                "environmental_memory":sum(s.memory)/n,"environmental_cohesion":sum(s.cohesion)/n,
                "prediction_error":sum(s.prediction_error)/n,"novelty":sum(s.prediction_error)/n,
                "estimated_work_units":float(len(s.bonds)+n)}
