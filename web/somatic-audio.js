/* Browser audio-to-body bridge. Call update() once per animation frame.
 * It reads only local WebAudio FFT magnitudes; it does not upload audio samples,
 * record audio, or send audio to a server.
 */
export class SomaticAudioBridge {
  constructor({audioContext,sourceNode,gpu,smoothing=0.18,minDb=-90,maxDb=-20,
    strength=4,spatialScale=2,center=[0,0,0],connectOutput=false}={}){
    if(!audioContext || !sourceNode || !gpu) throw new TypeError("audioContext, sourceNode and gpu are required");
    if(![smoothing,minDb,maxDb,strength,spatialScale,...center].every(Number.isFinite) ||
      smoothing<=0 || smoothing>1 || minDb>=maxDb || strength<0 || strength>20 ||
      spatialScale<=0 || spatialScale>100 || center.length!==3)
      throw new RangeError("Invalid audio bridge configuration");
    this.audioContext=audioContext;this.sourceNode=sourceNode;this.gpu=gpu;
    this.smoothing=smoothing;this.minDb=minDb;this.maxDb=maxDb;
    this.strength=strength;this.spatialScale=spatialScale;this.center=[...center];
    this.analyser=audioContext.createAnalyser();this.analyser.fftSize=2048;
    this.analyser.smoothingTimeConstant=0;
    this.frequencyData=new Float32Array(this.analyser.frequencyBinCount);
    this.bands=[0,0,0];this.disposed=false;
    sourceNode.connect(this.analyser);
    if(connectOutput)this.analyser.connect(audioContext.destination);
  }
  static fromMediaStream(stream,gpu,options={}){
    const AudioContextClass=globalThis.AudioContext || globalThis.webkitAudioContext;
    if(!AudioContextClass)throw new Error("Web Audio API unavailable");
    const context=new AudioContextClass();
    const source=context.createMediaStreamSource(stream);
    return new SomaticAudioBridge({audioContext:context,sourceNode:source,gpu,...options});
  }
  static fromAudioElement(element,gpu,options={}){
    const AudioContextClass=globalThis.AudioContext || globalThis.webkitAudioContext;
    if(!AudioContextClass)throw new Error("Web Audio API unavailable");
    const context=new AudioContextClass();
    const source=context.createMediaElementSource(element);
    return new SomaticAudioBridge({audioContext:context,sourceNode:source,gpu,connectOutput:true,...options});
  }
  bandLevel(lowHz,highHz){
    const hzPerBin=this.audioContext.sampleRate/this.analyser.fftSize;
    const lo=Math.max(0,Math.floor(lowHz/hzPerBin));
    const hi=Math.min(this.frequencyData.length,Math.max(lo+1,Math.ceil(highHz/hzPerBin)));
    let sum=0,count=0;
    for(let i=lo;i<hi;i++){
      const db=this.frequencyData[i];
      if(Number.isFinite(db)){
        const level=Math.max(0,Math.min(1,(db-this.minDb)/(this.maxDb-this.minDb)));
        sum+=level;count++;
      }
    }
    return count?sum/count:0;
  }
  update(){
    if(this.disposed)throw new Error("SomaticAudioBridge disposed");
    this.analyser.getFloatFrequencyData(this.frequencyData);
    const raw=[this.bandLevel(20,250),this.bandLevel(250,2000),this.bandLevel(2000,12000)];
    for(let i=0;i<3;i++)this.bands[i]+=this.smoothing*(raw[i]-this.bands[i]);
    const phase=this.audioContext.currentTime;
    this.gpu.setAudioDrive(this.bands[0],this.bands[1],this.bands[2],{
      strength:this.strength,spatialScale:this.spatialScale,phase,center:this.center
    });
    return {bass:this.bands[0],mid:this.bands[1],treble:this.bands[2]};
  }
  async resume(){if(this.disposed)throw new Error("SomaticAudioBridge disposed");if(this.audioContext.state!=="running")await this.audioContext.resume();}
  dispose({closeContext=false}={}){
    if(this.disposed)return;
    this.gpu.clearAudioDrive();this.sourceNode.disconnect(this.analyser);this.analyser.disconnect();
    if(closeContext)this.audioContext.close();
    this.disposed=true;
  }
}
