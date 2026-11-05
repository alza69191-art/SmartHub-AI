(() => {
 const $=id=>document.getElementById(id);let context=null,merged=null,blobUrl=null;
 const say=t=>$("status").textContent=t; $("volume").addEventListener("input",()=>$("volumeValue").textContent=$("volume").value+"%");
 const getContext=()=>context||(context=new (window.AudioContext||window.webkitAudioContext)());
 const wav=(buffer,start,end,volume=1,fadeIn=0,fadeOut=0)=>{
  const rate=buffer.sampleRate,from=Math.floor(start*rate),to=Math.min(buffer.length,Math.floor(end*rate)),length=to-from,channels=buffer.numberOfChannels;
  if(length<=0)throw Error("نطاق القص غير صالح.");
  const bytes=44+length*channels*2,view=new DataView(new ArrayBuffer(bytes));let p=0;
  const str=s=>{for(let i=0;i<s.length;i++)view.setUint8(p++,s.charCodeAt(i));};
  str("RIFF");view.setUint32(p,bytes-8,true);p+=4;str("WAVEfmt ");view.setUint32(p,16,true);p+=4;view.setUint16(p,1,true);p+=2;view.setUint16(p,channels,true);p+=2;view.setUint32(p,rate,true);p+=4;view.setUint32(p,rate*channels*2,true);p+=4;view.setUint16(p,channels*2,true);p+=2;view.setUint16(p,16,true);p+=2;str("data");view.setUint32(p,length*channels*2,true);p+=4;
  for(let i=0;i<length;i++)for(let c=0;c<channels;c++){let gain=volume;if(fadeIn>0)gain*=Math.min(1,i/rate/fadeIn);if(fadeOut>0)gain*=Math.min(1,(length-1-i)/rate/fadeOut);let v=Math.max(-1,Math.min(1,buffer.getChannelData(c)[from+i]*gain));view.setInt16(p,v<0?v*32768:v*32767,true);p+=2;}
  return new Blob([view],{type:"audio/wav"});
 };
 $("audioFiles").addEventListener("change",()=>{$("join").disabled=!$("audioFiles").files.length;$("audioInfo").textContent=$("audioFiles").files.length+" ملف/ملفات محددة.";});
 $("join").onclick=async()=>{
  const files=[...$("audioFiles").files];if(!files.length)return;
  $("join").disabled=true;say("جارٍ فك ترميز الملفات…");
  try{
   const ctx=getContext(),decoded=[];
   for(const f of files){if(!f.type.startsWith("audio/"))throw Error("أحد الملفات ليس ملفاً صوتياً.");decoded.push(await ctx.decodeAudioData(await f.arrayBuffer()));}
   const rate=Math.max(...decoded.map(b=>b.sampleRate)),channels=Math.max(...decoded.map(b=>b.numberOfChannels)),total=decoded.reduce((n,b)=>n+b.duration,0);
   if(total>900)throw Error("المدة الإجمالية تتجاوز 15 دقيقة في هذا الإصدار.");
   const frames=Math.ceil(total*rate),out=ctx.createBuffer(channels,frames,rate);let offset=0;
   for(const b of decoded){const targetLength=Math.ceil(b.duration*rate);for(let c=0;c<channels;c++){const src=b.getChannelData(Math.min(c,b.numberOfChannels-1)),dst=out.getChannelData(c);for(let i=0;i<targetLength;i++){const pos=i*b.sampleRate/rate,lo=Math.floor(pos),hi=Math.min(src.length-1,lo+1),frac=pos-lo;dst[offset+i]=(src[lo]||0)*(1-frac)+(src[hi]||0)*frac;}}offset+=targetLength;}
   merged=out;$("start").value=0;$("end").value=merged.duration.toFixed(2);$("play").disabled=false;$("export").disabled=false;say("تم الدمج: "+total.toFixed(2)+" ثانية، "+channels+" قناة صوتية.");
  }catch(e){say(e.message||"تعذر معالجة الملفات.");}
  finally{$("join").disabled=false;}
 };
 $("play").onclick=()=>{if(!merged)return;const b=wav(merged,Number($("start").value),Number($("end").value),Number($("volume").value)/100,Number($("fadeIn").value),Number($("fadeOut").value));if(blobUrl)URL.revokeObjectURL(blobUrl);blobUrl=URL.createObjectURL(b);$("preview").src=blobUrl;$("preview").style.display="block";$("preview").play();};
 $("export").onclick=()=>{if(!merged)return;try{const b=wav(merged,Number($("start").value),Number($("end").value),Number($("volume").value)/100,Number($("fadeIn").value),Number($("fadeOut").value));const u=URL.createObjectURL(b),a=document.createElement("a");a.href=u;a.download="smarthub-audio.wav";a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);say("تم تجهيز ملف WAV للتنزيل.");}catch(e){say(e.message);}};
 window.addEventListener("pagehide",()=>{if(blobUrl)URL.revokeObjectURL(blobUrl);if(context)context.close();});
})();