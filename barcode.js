(() => {
 const $=id=>document.getElementById(id);
 let stream=null,detector=null,loopId=null,lastValue="";
 const say=(text)=>{$("scanResult").textContent=text;};
 async function makeDetector(){
  if(!("BarcodeDetector" in window))throw Error("هذا المتصفح لا يدعم قارئ الباركود المدمج. جرّب Chrome أو Edge.");
  const formats=await BarcodeDetector.getSupportedFormats();
  const preferred=["qr_code","code_128","code_39","ean_13","ean_8","upc_a","upc_e","itf","codabar","data_matrix","pdf417","aztec"];
  detector=new BarcodeDetector({formats:preferred.filter(x=>formats.includes(x))});
 }
 async function readBitmap(bitmap){
  await makeDetector();
  const results=await detector.detect(bitmap);
  if(!results.length){say("لم يتم العثور على باركود في الصورة.");return;}
  lastValue=results[0].rawValue||"";
  say("النتيجة ("+(results[0].format||"barcode")+"): "+lastValue);
 }
 $("scanFile").addEventListener("change",async e=>{
  const file=e.target.files?.[0];if(!file)return;
  if(!file.type.startsWith("image/")){say("اختر ملف صورة صالحاً.");return;}
  try{const bitmap=await createImageBitmap(file);await readBitmap(bitmap);bitmap.close();}
  catch(err){say(err.message||"تعذرت قراءة الصورة.");}
 });
 $("cameraStart").onclick=async()=>{
  try{
   await makeDetector();
   stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:"environment"},audio:false});
   const video=$("camera");video.srcObject=stream;video.hidden=false;await video.play();
   $("cameraStart").disabled=true;$("cameraStop").disabled=false;
   const scan=async()=>{if(!stream)return;try{const found=await detector.detect(video);if(found.length){lastValue=found[0].rawValue||"";say("تمت القراءة: "+lastValue);stop();return;}}catch{}loopId=requestAnimationFrame(scan);};
   scan();
  }catch(err){say(err.message||"تعذر تشغيل الكاميرا. تحقق من الإذن واستخدم HTTPS.");}
 };
 function stop(){if(loopId)cancelAnimationFrame(loopId);loopId=null;if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}const v=$("camera");v.pause();v.srcObject=null;v.hidden=true;$("cameraStart").disabled=false;$("cameraStop").disabled=true;}
 $("cameraStop").onclick=stop;
 $("makeCode").onclick=()=>{
  const value=$("codeText").value.trim(),type=$("codeType").value,out=$("codeOutput");
  if(!value){say("أدخل نصاً أو رابطاً أولاً.");return;}
  out.replaceChildren();
  try{
   if(type==="qr"){
    if(!window.QRCode)throw Error("تعذر تحميل مكتبة QR.");
    const target=document.createElement("div");out.append(target);
    new QRCode(target,{text:value,width:240,height:240,correctLevel:QRCode.CorrectLevel.M});
   }else{
    if(!/^[\x20-\x7E]+$/.test(value)||value.length>80)throw Error("Code 128 يقبل هنا نص ASCII بطول أقصى 80 حرفاً. استخدم QR للرابط.");
    const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");out.append(svg);
    JsBarcode(svg,value,{format:"CODE128",displayValue:true,margin:12});
   }
   $("downloadCode").disabled=false;
  }catch(err){out.textContent=err.message;$("downloadCode").disabled=true;}
 };
 $("downloadCode").onclick=()=>{
  const out=$("codeOutput"),svg=out.querySelector("svg");
  if(svg){const xml=new XMLSerializer().serializeToString(svg),blob=new Blob([xml],{type:"image/svg+xml"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="smarthub-barcode.svg";a.click();URL.revokeObjectURL(url);return;}
  const canvas=out.querySelector("canvas");if(canvas){const a=document.createElement("a");a.href=canvas.toDataURL("image/png");a.download="smarthub-qr.png";a.click();return;}
  const img=out.querySelector("img");if(img){const a=document.createElement("a");a.href=img.src;a.download="smarthub-qr.png";a.click();}
 };

 $("makeImageQr").addEventListener("click",async()=>{
  const file=$("imageToQr").files?.[0];if(!file){say("اختر صورة أولاً.");return;}
  try{
   if(!file.type.startsWith("image/"))throw Error("الملف المحدد ليس صورة.");
   const bitmap=await createImageBitmap(file),c=document.createElement("canvas"),cx=c.getContext("2d");
   c.width=48;c.height=48;cx.fillStyle="#fff";cx.fillRect(0,0,48,48);
   const scale=Math.min(48/bitmap.width,48/bitmap.height),w=bitmap.width*scale,h=bitmap.height*scale;
   cx.drawImage(bitmap,(48-w)/2,(48-h)/2,w,h);bitmap.close();
   const blob=await new Promise(resolve=>c.toBlob(resolve,"image/jpeg",.2));if(!blob)throw Error("تعذر ضغط الصورة.");
   const dataUrl=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error("تعذر قراءة الصورة."));reader.readAsDataURL(blob);});
   if(dataUrl.length>1700)throw Error("الصورة لا تزال كبيرة على سعة QR. اختر صورة أبسط أو أصغر.");
   $("codeType").value="qr";$("codeText").value=dataUrl;$("makeCode").click();
   if(!$("codeOutput").querySelector("canvas,img"))throw Error($("codeOutput").textContent||"تعذر إنشاء QR لهذه الصورة.");
   say("تم إنشاء QR بصورة مصغرة مضمّنة. افحصه بهاتفك وتأكد من دعم قارئك لبيانات data URL.");
  }catch(err){say(err.message||"تعذر تحويل الصورة.");}
 });
 window.addEventListener("pagehide",stop);
})();