/* Versioned cognitive-goal receiver for the GPU-resident SomaticKernel.
 * It accepts only server-approved goal events. It never commits physiology.
 */
export class ChimeraBridge {
  constructor(kernel,{url="ws://127.0.0.1:8766",onStatus=()=>{},onGoal=()=>{}}={}) {
    if(!kernel||typeof kernel.setAttractor!=="function")throw new TypeError("kernel must expose setAttractor()");
    this.kernel=kernel;this.onStatus=onStatus;this.onGoal=onGoal;
    this.lastGoalSequence=0;this.lastWorldRevision=0;this.closed=false;
    this.ws=new WebSocket(url);
    this.ws.addEventListener("open",()=>this.onStatus({state:"connected"}));
    this.ws.addEventListener("close",()=>this.onStatus({state:"disconnected"}));
    this.ws.addEventListener("error",()=>this.onStatus({state:"error"}));
    this.ws.addEventListener("message",event=>this.#receive(event.data));
  }
  #receive(raw) {
    let message;
    try { message=JSON.parse(raw); } catch { this.onStatus({state:"invalid_json"}); return; }
    if(message?.type!=="MACRO_GOAL_UPDATE"||message.schema_version!==1)return;
    if(message.accepted!==true||typeof message.goal_id!=="string"||!message.goal_id)return;
    if(!Number.isSafeInteger(message.goal_sequence)||message.goal_sequence<=this.lastGoalSequence)return;
    if(!Number.isSafeInteger(message.world_revision)||message.world_revision<0)return;
    const t=message.target;
    if(!t||![t.x,t.y,t.z].every(Number.isFinite))return;
    const steering=message.steering??{};
    const strength=steering.strength??1;
    const maxAcceleration=steering.max_acceleration??8;
    if(!Number.isFinite(strength)||strength<0||!Number.isFinite(maxAcceleration)||maxAcceleration<0)return;
    this.lastGoalSequence=message.goal_sequence;
    this.lastWorldRevision=message.world_revision;
    this.kernel.setAttractor(t.x,t.y,t.z,{strength,maxAcceleration});
    this.onGoal({goalId:message.goal_id,goalSequence:message.goal_sequence,
      worldRevision:message.world_revision,target:{x:t.x,y:t.y,z:t.z}});
  }
  close() {
    if(this.closed)return;
    this.closed=true;
    this.ws.close(1000,"client shutdown");
  }
}
