(() => {
const $=id=>document.getElementById(id);
const api=(window.SMART_HUB_API_URL||"").replace(/\/$/,"");
let selectedFile=null;
$("image").addEventListener("change",()=>{
 selectedFile=$("image").files[0]||null;
 $("result").style.display="none";
 if(!selectedFile){$("preview").style.display="none";return;}
 if(!["image/png","image/jpeg","image/webp"].includes(selectedFile.type)){selectedFile=null;$("status").textContent="صيغة الصورة غير مدعومة.";return;}
 if(selectedFile.size>12*1024*1024){selectedFile=null;$("status").textContent="حجم الصورة يتجاوز 12 MB.";return;}
 $("preview").src=URL.createObjectURL(selectedFile);$("preview").style.display="block";$("status").textContent="";
});
$("edit").addEventListener("click",async()=>{
 const token=sessionStorage.getItem("sh-token");
 if(!token){$("status").textContent="سجّل الدخول أولاً من صفحة الحساب.";return;}
 const prompt=$("prompt").value.trim();
 if(!selectedFile){$("status").textContent="اختر صورة أولاً.";return;}
 if(prompt.length<3){$("status").textContent="اكتب تعليمات التعديل أولاً.";return;}
 const button=$("edit");button.disabled=true;$("result").style.display="none";$("status").textContent="جارٍ إرسال الصورة إلى Google Gemini لتعديلها...";
 try{
  const base64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(",")[1]);reader.onerror=reject;reader.readAsDataURL(selectedFile);});
  const response=await fetch(api+"/api/images/edit",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},body:JSON.stringify({prompt,image_base64:base64,mime_type:selectedFile.type})});
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(data.detail||"فشل تعديل الصورة");
  $("output").src=data.image;$("download").href=data.image;$("result").style.display="block";
  $("status").textContent="تم تعديل الصورة بنجاح باستخدام "+(data.provider||"Google Gemini")+".";
 }catch(error){$("status").textContent=error.message||"حدث خطأ أثناء تعديل الصورة."}
 finally{button.disabled=false}
});
})();