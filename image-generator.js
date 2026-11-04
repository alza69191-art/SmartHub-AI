(() => {
const $=id=>document.getElementById(id);
const api=(window.SMART_HUB_API_URL||"").replace(/\/$/,"");
$("generate").addEventListener("click",async()=>{
 const token=sessionStorage.getItem("sh-token");
 if(!token){$("status").textContent="سجّل الدخول أولاً من صفحة الحساب.";return;}
 const prompt=$("prompt").value.trim();
 if(prompt.length<3){$("status").textContent="اكتب وصفاً للصورة أولاً.";return;}
 const button=$("generate");button.disabled=true;$("result").style.display="none";$("status").textContent="جارٍ الاتصال بالنموذج وتجهيز الصورة. قد يستغرق ذلك عدة دقائق...";
 try{
  const response=await fetch(api+"/api/images/generate",{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},body:JSON.stringify({prompt,enhance_prompt:$("enhance").checked,quality:$("quality").value,custom_size:false,width:1024,height:1024,negative_prompt:$("negative").value,seed:Number($("seed").value)||0})});
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(data.detail||"فشل توليد الصورة");
  $("output").src=data.image;$("download").href=data.image;$("result").style.display="block";
  $("status").textContent="تم إنشاء الصورة بنجاح — Seed: "+data.seed;
 }catch(error){$("status").textContent=error.message||"حدث خطأ أثناء التوليد."}
 finally{button.disabled=false}
});
})();