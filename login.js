(() => {
const API=(window.SMART_HUB_API_URL||"").replace(/\/$/,""),$=id=>document.getElementById(id),form=$("loginForm"),msg=$("accountMessage");
const say=(s,bad=false)=>{msg.textContent=s;msg.classList.toggle("error",bad)};
const clearAuth=()=>{localStorage.removeItem("sh-token");localStorage.removeItem("sh-user");sessionStorage.removeItem("sh-token");sessionStorage.removeItem("sh-user")};
const token=()=>localStorage.getItem("sh-token")||sessionStorage.getItem("sh-token");
form.addEventListener("submit",async e=>{e.preventDefault();const b=form.querySelector('button:not([type="button"])');b.disabled=true;say("جارٍ التحقق من بياناتك...");
try{
 if(!API)throw Error("رابط الخادم غير مضبوط");
 const r=await fetch(API+"/api/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:$("loginEmail").value.trim(),password:$("loginPassword").value})});
 const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.detail||"تعذر تسجيل الدخول");
 clearAuth();
 const storage=$("rememberLogin").checked?localStorage:sessionStorage;
 storage.setItem("sh-token",d.token);storage.setItem("sh-user",JSON.stringify(d.user));
 say($("rememberLogin").checked?"تم تسجيل الدخول، وسيبقى الحساب محفوظاً على هذا الجهاز حتى انتهاء صلاحية الجلسة.":"تم تسجيل الدخول لهذه الجلسة.");
 location.href="support.html";
}catch(err){say(err.message,true)}finally{b.disabled=false}});
if(token()){
 $("authState").textContent=localStorage.getItem("sh-token")?"تم تفعيل تذكر تسجيل الدخول على هذا الجهاز.":"يوجد تسجيل دخول لهذه الجلسة.";
 $("logoutButton").hidden=false;
 $("logoutButton").onclick=()=>{clearAuth();say("تم تسجيل الخروج.");$("logoutButton").hidden=true;$("authState").textContent="غير مسجل"};
}
})();