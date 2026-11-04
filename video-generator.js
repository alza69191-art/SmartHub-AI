(() => {
const API=(window.SMART_HUB_API_URL||"").replace(/\/$/,"");
const $=id=>document.getElementById(id);
const token=sessionStorage.getItem("sh-token")||"";
const result=$("result"),status=$("status"),detail=$("detail"),video=$("output"),download=$("download"),button=$("generate");
let pollTimer=null;
function show(message,error=false){result.style.display="block";status.textContent=message;status.classList.toggle("video-error",error)}
async function call(path,options={}){
 const headers={"Content-Type":"application/json",...(options.headers||{})};
 if(token)headers.Authorization="Bearer "+token;
 const response=await fetch(API+path,{...options,headers});
 const data=await response.json().catch(()=>({}));
 if(!response.ok)throw new Error(data.detail||"حدث خطأ في الاتصال بالخادم");
 return data;
}
$("videoForm").addEventListener("submit",async event=>{
 event.preventDefault();
 if(!token){show("سجّل الدخول إلى SmartHub أولاً، ثم أعد المحاولة.",true);return}
 if(!API){show("رابط الخادم غير مضبوط.",true);return}
 if(pollTimer)clearTimeout(pollTimer);
 video.hidden=true;download.hidden=true;detail.textContent="";button.disabled=true;button.textContent="جارٍ إرسال الطلب...";
 show("جارٍ إرسال طلب إنشاء الفيديو إلى نموذج LTX...");
 try{
  const job=await call("/api/video/generate",{method:"POST",body:JSON.stringify({prompt:$("prompt").value.trim(),duration:Number($("duration").value),aspect_ratio:$("ratio").value})});
  detail.textContent="رقم المهمة: "+job.project_id+" · المحرك: LTX-Video";
  await poll(job.project_id);
 }catch(error){show(error.message,true);button.disabled=false;button.textContent="إنشاء الفيديو"}
});
async function poll(id){
 try{
  const data=await call("/api/video/status/"+encodeURIComponent(id));
  const labels={queued:"تم إدراج الفيديو في طابور GPU المجاني...",running:"النموذج يعمل على إنشاء الفيديو...",complete:"اكتمل توليد الفيديو.",error:"تعذر توليد الفيديو."};
  show(labels[data.status]||("حالة المهمة: "+data.status),data.status==="error");
  if(data.status==="complete"&&data.video_url){
   video.src=data.video_url;video.hidden=false;download.href=data.video_url;download.hidden=false;detail.textContent="اكتمل الفيديو. رابط التنزيل من مساحة النموذج وقد يكون مؤقتاً؛ حمّله الآن.";
   button.disabled=false;button.textContent="إنشاء فيديو آخر";return;
  }
  if(data.status==="error"){
   detail.textContent=data.error||"قد تكون مساحة النموذج متوقفة أو مشغولة. أعد المحاولة لاحقاً.";
   button.disabled=false;button.textContent="إعادة المحاولة";return;
  }
  pollTimer=setTimeout(()=>poll(id),6000);
 }catch(error){show(error.message,true);button.disabled=false;button.textContent="إعادة المحاولة"}
}
})();