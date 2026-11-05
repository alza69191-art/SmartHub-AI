(() => {
 const $=id=>document.getElementById(id);
 const fileInput=$("imageFile"),canvas=$("preview"),ctx=canvas.getContext("2d",{willReadFrequently:true});
 let source=null,sourceUrl=null,outputBlob=null;
 const say=(id,msg)=>$(id).textContent=msg;
 const bytes=n=>n<1024? n+" B":n<1048576?(n/1024).toFixed(1)+" KB":(n/1048576).toFixed(2)+" MB";
 function setOutput(id,suffix){$(id+"Value").textContent=suffix;}
 ["quality","brightness","contrast","sharpness"].forEach(id=>$(id).addEventListener("input",()=>{
  const suffix=id==="sharpness"?"": "%";setOutput(id,$(id).value+suffix);
 }));
 $("keepRatio").addEventListener("change",()=>{if(source&&$("keepRatio").checked){$("width").value=source.naturalWidth;$("height").value=source.naturalHeight;}});
 $("width").addEventListener("input",()=>{if(source&&$("keepRatio").checked&&$("width").value){$("height").value=Math.round(Number($("width").value)*source.naturalHeight/source.naturalWidth)||1;}});
 $("height").addEventListener("input",()=>{if(source&&$("keepRatio").checked&&$("height").value){$("width").value=Math.round(Number($("height").value)*source.naturalWidth/source.naturalHeight)||1;}});
 fileInput.addEventListener("change",()=>{
  const file=fileInput.files&&fileInput.files[0];if(!file)return;
  if(!file.type.startsWith("image/")){say("fileInfo","الملف المحدد ليس صورة.");return;}
  if(sourceUrl)URL.revokeObjectURL(sourceUrl);sourceUrl=URL.createObjectURL(file);source=new Image();
  source.onload=()=>{$("width").value=source.naturalWidth;$("height").value=source.naturalHeight;$("process").disabled=false;$("download").disabled=true;outputBlob=null;say("fileInfo",file.name+" — "+source.naturalWidth+" × "+source.naturalHeight+" — "+bytes(file.size));render();};
  source.onerror=()=>say("fileInfo","تعذر فتح الصورة.");
  source.src=sourceUrl;
 });
 function render(){
  if(!source)return;
  const w=Math.max(1,Math.min(12000,Number($("width").value)||source.naturalWidth));
  const h=Math.max(1,Math.min(12000,Number($("height").value)||source.naturalHeight));
  canvas.width=w;canvas.height=h;ctx.filter="brightness("+$("brightness").value+"%) contrast("+$("contrast").value+"%)";
  ctx.drawImage(source,0,0,w,h);ctx.filter="none";
  const amount=Number($("sharpness").value);
  if(amount>0&&w*h<=16000000){
   const image=ctx.getImageData(0,0,w,h),src=image.data,out=new Uint8ClampedArray(src),k=amount*.18;
   for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){const i=(y*w+x)*4,neighbors=[i-4,i+4,i-w*4,i+w*4];for(let c=0;c<3;c++){let v=src[i+c]* (1+4*k);for(const ni of neighbors)v-=src[ni+c]*k;out[i+c]=Math.max(0,Math.min(255,v));}}
   image.data.set(out);ctx.putImageData(image,0,0);
  }else if(amount>0){say("resultInfo","تم تجاوز تطبيق الحدة لتجنب استهلاك ذاكرة كبير؛ خفّض الأبعاد.");}
  canvas.hidden=false;
 }
 $("process").addEventListener("click",()=>{
  if(!source)return;render();const type=$("format").value,q=Number($("quality").value)/100;
  canvas.toBlob(blob=>{if(!blob){say("resultInfo","تعذر تصدير الصورة بهذه الصيغة؛ جرّب PNG أو JPEG.");return;}outputBlob=blob;$("download").disabled=false;say("resultInfo","الحجم الناتج: "+bytes(blob.size)+" — الأبعاد: "+canvas.width+" × "+canvas.height+" — "+blob.type);},type,type==="image/png"?undefined:q);
 });
 $("download").addEventListener("click",()=>{if(!outputBlob)return;const url=URL.createObjectURL(outputBlob),a=document.createElement("a"),ext=outputBlob.type==="image/png"?"png":outputBlob.type==="image/jpeg"?"jpg":"webp";a.href=url;a.download="smarthub-image."+ext;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
 window.addEventListener("pagehide",()=>{if(sourceUrl)URL.revokeObjectURL(sourceUrl);});
})();