(() => {
 const $=id=>document.getElementById(id),fileInput=$("imageFile"),canvas=$("preview"),ctx=canvas.getContext("2d",{willReadFrequently:true});
 let source=null,sourceUrl=null,outputBlob=null,loadSequence=0;
 const MAX_OUTPUT_PIXELS=24000000;
 const say=(id,msg)=>$(id).textContent=msg;
 const bytes=n=>n<1024?n+" B":n<1048576?(n/1024).toFixed(1)+" KB":(n/1048576).toFixed(2)+" MB";
 const val=(id,fallback,min,max)=>Math.max(min,Math.min(max,Number($(id).value)||fallback));
 ["quality","brightness","contrast","sharpness","watermarkOpacity"].forEach(id=>$(id).addEventListener("input",()=>{
  const suffix=id==="sharpness"?"": "%";const out=$(id+"Value");if(out)out.textContent=$(id).value+suffix;
 }));
 function cropRect(){
  const sw=source.naturalWidth,sh=source.naturalHeight;
  const x=val("cropX",0,0,99)/100,y=val("cropY",0,0,99)/100;
  const w=Math.min(val("cropW",100,1,100)/100,1-x),h=Math.min(val("cropH",100,1,100)/100,1-y);
  return {x:Math.floor(sw*x),y:Math.floor(sh*y),w:Math.max(1,Math.floor(sw*w)),h:Math.max(1,Math.floor(sh*h))};
 }
 function updateDimensions(){
  if(!source)return;const r=cropRect();
  $("width").value=r.w;$("height").value=r.h;
 }
 ["cropX","cropY","cropW","cropH"].forEach(id=>$(id).addEventListener("change",updateDimensions));
 $("keepRatio").addEventListener("change",()=>{if(source&&$("keepRatio").checked)updateDimensions();});
 $("width").addEventListener("input",()=>{if(source&&$("keepRatio").checked){const r=cropRect();$("height").value=Math.max(1,Math.round((Number($("width").value)||r.w)*r.h/r.w));}});
 $("height").addEventListener("input",()=>{if(source&&$("keepRatio").checked){const r=cropRect();$("width").value=Math.max(1,Math.round((Number($("height").value)||r.h)*r.w/r.h));}});
 fileInput.addEventListener("change",()=>{
  const sequence=++loadSequence,file=fileInput.files&&fileInput.files[0];
  if(sourceUrl)URL.revokeObjectURL(sourceUrl);sourceUrl=null;source=null;outputBlob=null;
  $("process").disabled=true;$("download").disabled=true;canvas.hidden=true;say("resultInfo","");
  if(!file){say("fileInfo","");return;}
  if(!file.type.startsWith("image/")){fileInput.value="";say("fileInfo","الملف المحدد ليس صورة.");return;}
  if(file.size>25*1024*1024){fileInput.value="";say("fileInfo","حجم الصورة يتجاوز 25 ميغابايت لتجنب استهلاك ذاكرة المتصفح.");return;}
  sourceUrl=URL.createObjectURL(file);const candidate=new Image();
  candidate.onload=()=>{if(sequence!==loadSequence)return;if(candidate.naturalWidth*candidate.naturalHeight>MAX_OUTPUT_PIXELS){source=null;URL.revokeObjectURL(sourceUrl);sourceUrl=null;fileInput.value="";say("fileInfo","أبعاد الصورة تتجاوز 24 ميغابكسل؛ اختر صورة أصغر.");return;}source=candidate;["cropX","cropY"].forEach(id=>$(id).value=0);["cropW","cropH"].forEach(id=>$(id).value=100);updateDimensions();$("process").disabled=false;$("download").disabled=true;say("fileInfo",file.name+" — "+source.naturalWidth+" × "+source.naturalHeight+" — "+bytes(file.size));render();};
  candidate.onerror=()=>{if(sequence!==loadSequence)return;source=null;if(sourceUrl)URL.revokeObjectURL(sourceUrl);sourceUrl=null;fileInput.value="";say("fileInfo","تعذر فتح الصورة.");};candidate.src=sourceUrl;
 });
 function render(){
  if(!source)return false;
  const r=cropRect(),w=val("width",r.w,1,12000),h=val("height",r.h,1,12000),rotation=Number($("rotation").value)||0;
  const swap=rotation===90||rotation===270;
  if(w*h>MAX_OUTPUT_PIXELS){say("resultInfo","الأبعاد المطلوبة تتجاوز 24 ميغابكسل. قلّل العرض أو الارتفاع.");$("download").disabled=true;outputBlob=null;return false;}
  canvas.width=swap?h:w;canvas.height=swap?w:h;
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.save();ctx.filter="brightness("+val("brightness",100,50,150)+"%) contrast("+val("contrast",100,50,150)+"%)";
  ctx.translate(canvas.width/2,canvas.height/2);ctx.rotate(rotation*Math.PI/180);
  ctx.scale($("flipX").checked?-1:1,$("flipY").checked?-1:1);
  ctx.drawImage(source,r.x,r.y,r.w,r.h,-w/2,-h/2,w,h);ctx.restore();ctx.filter="none";
  const amount=Number($("sharpness").value);
  if(amount>0&&canvas.width*canvas.height<=16000000){
   const image=ctx.getImageData(0,0,canvas.width,canvas.height),src=image.data,out=new Uint8ClampedArray(src),k=amount*.18;
   for(let y=1;y<canvas.height-1;y++)for(let x=1;x<canvas.width-1;x++){const i=(y*canvas.width+x)*4,neighbors=[i-4,i+4,i-canvas.width*4,i+canvas.width*4];for(let c=0;c<3;c++){let v=src[i+c]*(1+4*k);for(const ni of neighbors)v-=src[ni+c]*k;out[i+c]=Math.max(0,Math.min(255,v));}}
   image.data.set(out);ctx.putImageData(image,0,0);
  }else if(amount>0){say("resultInfo","تم تجاوز تطبيق الحدة لتجنب استهلاك ذاكرة كبير؛ خفّض الأبعاد.");}
  const mark=$("watermark").value.trim();
  if(mark){const size=Math.max(16,Math.round(canvas.width*.035));ctx.save();ctx.globalAlpha=val("watermarkOpacity",65,10,100)/100;ctx.fillStyle=$("watermarkColor").value;ctx.font="bold "+size+"px sans-serif";ctx.textAlign="right";ctx.textBaseline="bottom";ctx.shadowColor="#000";ctx.shadowBlur=Math.max(2,size*.12);ctx.fillText(mark,canvas.width-size*.6,canvas.height-size*.6,canvas.width-size*1.2);ctx.restore();}
  canvas.hidden=false;return true;
 }
 ["rotation","flipX","flipY","watermark","watermarkColor","cropX","cropY","cropW","cropH"].forEach(id=>$(id).addEventListener("change",()=>{if(source)render();}));
 $("watermark").addEventListener("input",()=>{if(source)render();});
 ["brightness","contrast","sharpness"].forEach(id=>$(id).addEventListener("input",()=>{if(source)render();}));
 $("process").addEventListener("click",()=>{
  if(!source||!render())return;const type=$("format").value,q=Number($("quality").value)/100;
  canvas.toBlob(blob=>{if(!blob){say("resultInfo","تعذر تصدير الصورة بهذه الصيغة؛ جرّب PNG أو JPEG.");return;}outputBlob=blob;$("download").disabled=false;say("resultInfo","الحجم الناتج: "+bytes(blob.size)+" — الأبعاد: "+canvas.width+" × "+canvas.height+" — "+blob.type);},type,type==="image/png"?undefined:q);
 });
 $("download").addEventListener("click",()=>{if(!outputBlob)return;const url=URL.createObjectURL(outputBlob),a=document.createElement("a"),ext=outputBlob.type==="image/png"?"png":outputBlob.type==="image/jpeg"?"jpg":"webp";a.href=url;a.download="smarthub-image."+ext;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
 window.addEventListener("pagehide",()=>{loadSequence++;if(sourceUrl)URL.revokeObjectURL(sourceUrl);sourceUrl=null;});
})();