(() => {
 const $=id=>document.getElementById(id);
 const input=$("videoFiles"),list=$("mergeList"),canvas=$("preview"),ctx=canvas.getContext("2d");
 let files=[],resultUrl=null,recorder=null,raf=0,stream=null,audioContext=null,audioDestination=null,sourceNode=null;
 const say=t=>$("status").textContent=t;
 const revoke=()=>{if(resultUrl){URL.revokeObjectURL(resultUrl);resultUrl=null;}};
 function renderList(){
  list.replaceChildren();
  files.forEach((file,index)=>{
   const row=document.createElement("div");row.className="merge-item";
   const label=document.createElement("span");label.textContent=(index+1)+". "+file.name;
   const size=document.createElement("small");size.textContent=(file.size/1048576).toFixed(1)+" MB";
   const up=document.createElement("button");up.type="button";up.className="action alt";up.textContent="↑";up.disabled=index===0;up.setAttribute("aria-label","تحريك للأعلى");up.onclick=()=>{[files[index-1],files[index]]=[files[index],files[index-1]];renderList();};
   const down=document.createElement("button");down.type="button";down.className="action alt";down.textContent="↓";down.disabled=index===files.length-1;down.setAttribute("aria-label","تحريك للأسفل");down.onclick=()=>{[files[index+1],files[index]]=[files[index],files[index+1]];renderList();};
   const remove=document.createElement("button");remove.type="button";remove.className="action alt";remove.textContent="حذف";remove.onclick=()=>{files.splice(index,1);renderList();};
   row.append(label,size,up,down,remove);list.append(row);
  });
  $("fileInfo").textContent=files.length+" ملف/ملفات — "+(files.reduce((n,f)=>n+f.size,0)/1048576).toFixed(1)+" MB";
  $("merge").disabled=files.length<2;
 }
 input.addEventListener("change",()=>{files=[...input.files].filter(f=>f.type.startsWith("video/"));revoke();$("download").disabled=true;renderList();say(files.length>=2?"رتّب المقاطع ثم اضغط دمج.":"اختر مقطعين صالحين على الأقل.");});
 function waitEvent(el,event,timeout=15000){return new Promise((resolve,reject)=>{const done=()=>{clean();resolve();},fail=()=>{clean();reject(Error("تعذر تحميل أحد مقاطع الفيديو."));},timer=setTimeout(()=>{clean();reject(Error("انتهت مهلة تحميل الفيديو."));},timeout),clean=()=>{clearTimeout(timer);el.removeEventListener(event,done);el.removeEventListener("error",fail);};el.addEventListener(event,done,{once:true});el.addEventListener("error",fail,{once:true});});}
 $("merge").addEventListener("click",async()=>{
  if(files.length<2||!window.MediaRecorder||!HTMLCanvasElement.prototype.captureStream){say("المتصفح لا يدعم تسجيل الفيديو من Canvas.");return;}
  $("merge").disabled=true;$("download").disabled=true;revoke();cancelAnimationFrame(raf);
  const video=document.createElement("video");video.playsInline=true;video.preload="auto";video.muted=false;
  const urls=files.map(f=>URL.createObjectURL(f));let chunks=[];
  try{
   audioContext=new (window.AudioContext||window.webkitAudioContext)();await audioContext.resume();audioDestination=audioContext.createMediaStreamDestination();sourceNode=audioContext.createMediaElementSource(video);sourceNode.connect(audioDestination);sourceNode.connect(audioContext.destination);
   const first=video;first.src=urls[0];await waitEvent(first,"loadedmetadata");
   const width=Math.min(1920,Math.max(640,first.videoWidth||1280)),height=Math.min(1080,Math.max(360,first.videoHeight||720));canvas.width=width;canvas.height=height;canvas.hidden=false;
   const videoStream=canvas.captureStream(30);stream=new MediaStream([...videoStream.getVideoTracks(),...audioDestination.stream.getAudioTracks()]);
   const mime=["video/webm;codecs=vp9,opus","video/webm;codecs=vp8,opus","video/webm"].find(t=>MediaRecorder.isTypeSupported(t));if(!mime)throw Error("لا يوجد ترميز WebM مدعوم.");
   recorder=new MediaRecorder(stream,{mimeType:mime});recorder.ondataavailable=e=>{if(e.data&&e.data.size)chunks.push(e.data);};
   const stopped=new Promise(resolve=>{recorder.onstop=resolve;});
   recorder.start(500);say("جارٍ دمج "+files.length+" مقاطع… لا تغلق الصفحة.");
   let drawing=true;
   const draw=()=>{if(!drawing)return;if(video.readyState>=2){ctx.fillStyle="#000";ctx.fillRect(0,0,width,height);const scale=Math.min(width/video.videoWidth,height/video.videoHeight),w=video.videoWidth*scale,h=video.videoHeight*scale;ctx.drawImage(video,(width-w)/2,(height-h)/2,w,h);}raf=requestAnimationFrame(draw);};
   draw();
   for(let i=0;i<urls.length;i++){
    video.pause();video.src=urls[i];video.load();await waitEvent(video,"loadedmetadata");
    await new Promise(async(resolve,reject)=>{video.onended=resolve;video.onerror=()=>reject(Error("تعذر تشغيل المقطع رقم "+(i+1)));try{await video.play();}catch(e){reject(e);}});
   }
   drawing=false;cancelAnimationFrame(raf);recorder.stop();await stopped;
   const blob=new Blob(chunks,{type:mime});if(!blob.size)throw Error("لم يتم إنشاء ملف؛ جرّب ملفات أخرى أو متصفحاً حديثاً.");
   resultUrl=URL.createObjectURL(blob);$("download").disabled=false;say("اكتمل الدمج. حجم الملف: "+(blob.size/1048576).toFixed(2)+" MB.");
  }catch(e){if(recorder&&recorder.state!=="inactive")recorder.stop();say(e.message||"تعذر دمج المقاطع.");}
  finally{cancelAnimationFrame(raf);if(stream)stream.getTracks().forEach(t=>t.stop());stream=null;if(audioContext){await audioContext.close().catch(()=>{});audioContext=null;}sourceNode=null;audioDestination=null;video.pause();video.removeAttribute("src");video.load();urls.forEach(URL.revokeObjectURL);$("merge").disabled=files.length<2;}
 });
 $("download").addEventListener("click",()=>{if(!resultUrl)return;const a=document.createElement("a");a.href=resultUrl;a.download="smarthub-merged-video.webm";a.click();});
 window.addEventListener("pagehide",()=>{cancelAnimationFrame(raf);if(stream)stream.getTracks().forEach(t=>t.stop());revoke();});
})();