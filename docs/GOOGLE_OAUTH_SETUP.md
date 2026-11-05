# إعداد تسجيل الدخول عبر Google

هذا الدليل خاص بتدفق Google Identity Services المستخدم في `google-auth.js`، حيث يعيد Google رمز ID Credential إلى الصفحة، ثم يتحقق منه خادم FastAPI عبر `GOOGLE_CLIENT_ID`.

## 1. إنشاء OAuth Client ID

1. افتح [Google Cloud Console](https://console.cloud.google.com/).
2. اختر مشروعاً أو أنشئ مشروعاً جديداً.
3. أكمل إعداد Google Auth Platform / شاشة موافقة OAuth، وأضف المستخدمين التجريبيين إذا كانت حالة التطبيق Testing.
4. من Clients أنشئ OAuth Client من النوع **Web application**.
5. ضمن **Authorized JavaScript origins** أضف هذا الأصل فقط:

   `https://alza69191-art.github.io`

   لا تضف المسار `/SmartHub-AI`؛ حقول Origins تقبل الأصل (scheme + host + port) ولا تقبل مسار الصفحة.
6. لا تضف Authorized redirect URI لهذا التدفق؛ الكود يستخدم GIS JavaScript popup callback ولا يستخدم redirect flow.
7. انسخ **Client ID** الذي ينتهي عادةً بـ `.apps.googleusercontent.com`.

## 2. ضبط الواجهة

في ملف `config.js` ضمن جذر GitHub Pages، عيّن قيمة Client ID العامة:

```js
window.SMART_HUB_API_URL = "https://smarthub-ai-api.onrender.com";
window.SMART_HUB_GOOGLE_CLIENT_ID = "YOUR_CLIENT_ID.apps.googleusercontent.com";
```

Client ID ليس كلمة مرور، لكنه يجب أن يكون مقيداً بالأصل المصرح به في Google Cloud. لا تضع Client Secret أو أي مفتاح خادم في ملفات الواجهة أو GitHub.

## 3. ضبط Render

في خدمة API على Render، أضف متغير البيئة:

- `GOOGLE_CLIENT_ID` = نفس Client ID المستخدم في `config.js`.
- `FRONTEND_ORIGIN` = `https://alza69191-art.github.io`

احتفظ بـ `JWT_SECRET` و`DATABASE_URL` في Render فقط. هذا التنفيذ يتحقق من Google ID token باستخدام Client ID؛ لا يحتاج إلى Client Secret في هذا التدفق.

بعد حفظ متغيرات البيئة، أعد نشر خدمة API إذا لم يبدأ Render النشر تلقائياً.

## 4. اختبار إلزامي قبل الإعلان عن جاهزية الميزة

1. افتح `https://alza69191-art.github.io/SmartHub-AI/account.html`.
2. تأكد من ظهور زر Google بدلاً من رسالة أن تسجيل Google غير مفعّل.
3. اختبر الدخول مع إلغاء خيار «إبقائي مسجلاً» ثم مع تفعيله.
4. تحقق من انتقال المستخدم إلى صفحة الدعم، ومن بقاء الجلسة بعد تحديث الصفحة.
5. اختبر رمزاً غير صالح؛ يجب أن يرفضه الخادم.
6. راجع سجلات Render وتأكد من عدم تسجيل credential أو JWT.

## ملاحظات

- وجود Client ID وحده لا يثبت أن تسجيل الدخول يعمل؛ يجب اختبار الواجهة وRender وقاعدة البيانات فعلياً.
- لا تشارك Client Secret أو JWT أو بيانات اعتماد Google في المحادثات أو ملفات المستودع.
- إذا ظهر خطأ `origin_mismatch`، راجع Authorized JavaScript origins وتأكد من تطابق البروتوكول والنطاق تماماً.
