(() => {
 const api=(window.SMART_HUB_API_URL||"").replace(/\/$/,"");
 const clientId=window.SMART_HUB_GOOGLE_CLIENT_ID||"";
 const host=document.getElementById("googleSignIn");
 if(!host)return;
 if(!clientId){host.innerHTML='<p class="hint">تسجيل Google غير مفعّل بعد. يلزم ضبط Google Client ID.</p>';return;}
 const script=document.createElement("script");
 script.src="https://accounts.google.com/gsi/client";script.async=true;script.defer=true;
 script.onload=()=>{
  google.accounts.id.initialize({client_id:clientId,callback:async response=>{
   try{
    const res=await fetch(api+"/api/auth/google",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({credential:response.credential,remember_me:!!document.getElementById("rememberMe")?.checked})});
    const data=await res.json().catch(()=>({}));
    if(!res.ok)throw Error(data.detail||"تعذر تسجيل الدخول عبر Google");
    if(document.getElementById("rememberMe")?.checked){localStorage.setItem("sh-token",data.token);localStorage.setItem("sh-user",JSON.stringify(data.user));sessionStorage.removeItem("sh-token");sessionStorage.removeItem("sh-user");}else{sessionStorage.setItem("sh-token",data.token);sessionStorage.setItem("sh-user",JSON.stringify(data.user));localStorage.removeItem("sh-token");localStorage.removeItem("sh-user");}
    location.href="support.html";
   }catch(error){
    const msg=document.getElementById("accountMessage");
    if(msg){msg.textContent=error.message;msg.classList.add("error");}
   }
  }});
  google.accounts.id.renderButton(host,{theme:"filled_black",size:"large",shape:"rectangular",width:280,text:"continue_with"});
 };
 document.head.appendChild(script);
})();