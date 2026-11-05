(() => {
 const $=id=>document.getElementById(id);
 const video=$("sourceVideo"),input=$("videoFile");
 let objectUrl=null,outputUrl=null,outputBlob=null,recorder=null,parts=[],capture=null,stopTimer=null;
 const say=t=>$("status").textContent=t;
 const supported=()=>!!(window.MediaRecorder&&(video.captureStream||video.mozCaptureStream));
 function cleanupCapture(){if(stopTimer)clearTimeout(stopTimer);stopTimer=null;if(capture){capture.getTracks().forEach(t=>t.stop());capture=null;}recorder=null;}
 input.addEventListener("change",()=>{
  const file=input.files&&input.files[0];if(!file)return;
  if(!file.type.startsWith("video/")){say("اختر ملف فيديو صالحاً.");return;}
  if(objectUrl)URL.revokeObjectURL(objectUrl);if(outputUrl)URL.revokeObjectURL(outputUrl);
  outputUrl=null;outputBlob=null;$("download").disabled=true;
  objectUrl=URL.createObjectURL(file);video.src=objectUrl;video.style.display="block";
  video.onloadedmetadata=()=>{$("startTime").value=0;$("endTime").value=video.duration.toFixed(2);$("export").disabled=!supported();$("fileInfo").textContent=file.name+" — "+video.videoWidth+" × "+video.videoHeight+" — "+video.duration.toFixed(2)+" ثانية";say(supported()?"حدد بداية ونهاية المقطع.":"متصفحك لا يدعم تسجيل الفيديو المطلوب (MediaRecorder/captureStream).");};
 });
 $("export").addEventListener("click",async()=>{
  if(!video.src||!supported())return;
  const start=Number($("startTime").value),end=Number($("endTime").value);
  if(!Number.isFinite(start)||!Number.isFinite(end)||start<0||end<=start||end>video.duration){say("تحقق من الوقت: النهاية يجب أن تكون بعد البداية وضمن مدة الفيديو.");return;}
  cleanupCapture();parts=[];outputBlob=null;$("download").disabled=true;
  try{
   video.pause();video.currentTime=start;
   await new Promise((resolve,reject)=>{const done=()=>{video.removeEventListener("seeked",done);resolve();};video.addEventListener("seeked",done,{once:true});setTimeout(()=>{video.removeEventListener("seeked",done);reject(Error("تعذر الانتقال إلى وقت البداية."));},5000);});
   capture=(video.captureStream||video.mozCaptureStream).call(video);
   const types=["video/webm;codecs=vp9,opus","video/webm;codecs=vp8,opus","video/webm"];
   const mime=types.find(t=>MediaRecorder.isTypeSupported(t));
   if(!mime)throw Error("لا يوجد ترميز WebM مدعوم في هذا المتصفح.");
   recorder=new MediaRecorder(capture,{mimeType:mime});
   recorder.ondataavailable=e=>{if(e.data&&e.data.size)parts.push(e.data);};
   recorder.onerror=()=>{cleanupCapture();say("حدث خطأ أثناء تسجيل المقطع.");};
   recorder.onstop=()=>{
    outputBlob=new Blob(parts,{type:mime});if(outputUrl)URL.revokeObjectURL(outputUrl);outputUrl=URL.createObjectURL(outputBlob);
    $("download").disabled=!outputBlob.size;cleanupCapture();
    say(outputBlob.size?"اكتمل القص. حجم الملف: "+(outputBlob.size/1048576).toFixed(2)+" MB":"لم ينتج ملف؛ تحقق من دعم المتصفح للترميز.");
   };
   recorder.start(250);say("جارٍ تسجيل المقطع المحدد…");await video.play();
   const check=()=>{if(!recorder||recorder.state!=="recording")return;if(video.currentTime>=end||video.ended){video.pause();recorder.stop();return;}stopTimer=setTimeout(check,80);};
   check();
  }catch(err){cleanupCapture();video.pause();say(err.message||"تعذر تصدير المقطع.");}
 });
 $("download").addEventListener("click",()=>{if(!outputUrl)return;const a=document.createElement("a");a.href=outputUrl;a.download="smarthub-trimmed-video.webm";a.click();});
 window.addEventListener("pagehide",()=>{cleanupCapture();if(objectUrl)URL.revokeObjectURL(objectUrl);if(outputUrl)URL.revokeObjectURL(outputUrl);});
})();