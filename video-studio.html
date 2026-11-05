import { FFmpeg } from "https://cdn.jsdelivr.net/npm/@ffmpeg/ffmpeg@0.12.10/dist/esm/index.js";
import { toBlobURL } from "https://cdn.jsdelivr.net/npm/@ffmpeg/util@0.12.2/dist/esm/index.js";
const $=id=>document.getElementById(id);let ffmpeg=null,loaded=false,resultUrl=null,resultName="";
const say=t=>$("status").textContent=t;
async function loadEngine(){if(loaded)return;const core="https://cdn.jsdelivr.net/npm/@ffmpeg/core@0.12.6/dist/umd";ffmpeg=new FFmpeg();ffmpeg.on("log",({message})=>{if(message&&/error/i.test(message))say(message.slice(-500));});ffmpeg.on("progress",({progress})=>$("progress").value=Math.max(0,Math.min(100,Math.round(progress*100))));say("جارٍ تنزيل محرك FFmpeg…");await ffmpeg.load({coreURL:await toBlobURL(core+"/ffmpeg-core.js","text/javascript"),wasmURL:await toBlobURL(core+"/ffmpeg-core.wasm","application/wasm")});loaded=true;}
function safeName(file){return file.name.replace(/[^a-zA-Z0-9._-]/g,"_").slice(-90)||"input.mp4";}
async function writeFile(file,name){await ffmpeg.writeFile(name,new Uint8Array(await file.arrayBuffer()));}
async function finish(name,type){const bytes=await ffmpeg.readFile(name);const blob=new Blob([bytes.buffer],{type});if(resultUrl)URL.revokeObjectURL(resultUrl);resultUrl=URL.createObjectURL(blob);resultName=name;$("download").disabled=false;say("اكتملت المعالجة. الحجم الناتج: "+(blob.size/1048576).toFixed(2)+" MB");}
$("operation").addEventListener("change",()=>{$("files").multiple=$("operation").value==="merge";});
$("run").addEventListener("click",async()=>{const files=[...$("files").files],op=$("operation").value;if(!files.length){say("اختر ملف فيديو أولاً.");return;}if(files.some(f=>!f.type.startsWith("video/"))){say("تأكد أن جميع الملفات فيديو.");return;}if(files.reduce((n,f)=>n+f.size,0)>250*1024*1024){say("إجمالي الملفات يتجاوز 250 ميغابايت. اختر مقاطع أصغر.");return;}if(op==="merge"&&files.length<2){say("اختر مقطعين على الأقل للدمج.");return;}if(op!=="merge"&&files.length!==1){say("اختر ملفاً واحداً لهذه العملية.");return;}
$("run").disabled=true;$("download").disabled=true;$("progress").value=0;try{await loadEngine();const inputs=[];for(let i=0;i<files.length;i++){const name="input"+i+"."+((files[i].name.split(".").pop()||"mp4").toLowerCase().replace(/[^a-z0-9]/g,"")||"mp4");await writeFile(files[i],name);inputs.push(name);}
let output="smarthub-output.mp4",args=[];
if(op==="trim"){const start=Math.max(0,Number($("start").value)||0),duration=Number($("duration").value);args=["-ss",String(start),"-i",inputs[0]];if(Number.isFinite(duration)&&duration>0)args.push("-t",String(duration));args.push("-c:v","libx264","-preset","ultrafast","-crf","26","-c:a","aac",output);}
else if(op==="merge"){const list=inputs.map(n=>"file '"+n+"'").join("\n");await ffmpeg.writeFile("concat-list.txt",new TextEncoder().encode(list));args=["-f","concat","-safe","0","-i","concat-list.txt","-c:v","libx264","-preset","ultrafast","-crf","26","-c:a","aac",output];}
else if(op==="compress")args=["-i",inputs[0],"-vf","scale='min(1280,iw)':-2","-c:v","libx264","-preset","ultrafast","-crf","30","-c:a","aac","-b:a","128k",output];
else if(op==="convert")args=["-i",inputs[0],"-c:v","libx264","-preset","ultrafast","-crf","24","-c:a","aac",output];
else if(op==="audio"){output="smarthub-audio.mp3";args=["-i",inputs[0],"-vn","-b:a","192k",output];}
else if(op==="mute")args=["-i",inputs[0],"-an","-c:v","libx264","-preset","ultrafast","-crf","24",output];
else {const filter=op==="rotate90"?"transpose=1":op==="rotate180"?"hflip,vflip":"transpose=2";args=["-i",inputs[0],"-vf",filter,"-c:v","libx264","-preset","ultrafast","-crf","24","-c:a","aac",output];}
say("جارٍ تنفيذ العملية: "+op+"…");const code=await ffmpeg.exec(args);if(code!==0)throw Error("تعذر تنفيذ العملية. قد لا يدعم ملفك الترميز المطلوب.");await finish(output,op==="audio"?"audio/mpeg":"video/mp4");for(const n of [...inputs,"concat-list.txt",output]){try{await ffmpeg.deleteFile(n);}catch{}}}catch(e){say("فشلت المعالجة: "+(e.message||e)+"\nجرّب ملفاً أصغر أو صيغة فيديو مختلفة.");}finally{$("run").disabled=false;}});
$("download").addEventListener("click",()=>{if(!resultUrl)return;const a=document.createElement("a");a.href=resultUrl;a.download=resultName;a.click();});
window.addEventListener("pagehide",()=>{if(resultUrl)URL.revokeObjectURL(resultUrl);});
