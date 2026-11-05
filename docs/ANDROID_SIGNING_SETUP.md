# إعداد توقيع إصدار SmartHub AI

لا ترفع نسخة Debug أو APK/AAB غير موقّع إلى متجر التطبيقات. هذا الإعداد يبني إصدار Release ويوقّعه داخل GitHub Actions باستخدام مفتاحك الخاص المخزّن في GitHub Secrets.

## 1) إنشاء مفتاح الإصدار على جهازك

ثبّت Java JDK إن لم يكن مثبتاً، ثم افتح PowerShell في مجلد خاص وآمن ونفّذ:

```powershell
keytool -genkeypair -v -keystore smarthub-release.jks -alias smarthub-release -keyalg RSA -keysize 4096 -validity 10000
```

اختر كلمة مرور قوية. احتفظ بملف `smarthub-release.jks` وكلمات المرور في مكانين آمنين. فقدان المفتاح قد يمنع تحديث التطبيق المنشور بنفس هوية التوقيع.

## 2) تجهيز قيمة Base64

من نفس مجلد الملف في PowerShell:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes(".\smarthub-release.jks")) | Set-Clipboard
```

هذا ينسخ قيمة Base64 إلى الحافظة. لا ترسلها في المحادثات ولا تضعها في ملفات المستودع.

## 3) إضافة GitHub Actions Secrets

افتح مستودع SmartHub AI ثم:
Settings → Secrets and variables → Actions → New repository secret

أنشئ هذه الأسرار الأربعة:

- `ANDROID_KEYSTORE_BASE64`: قيمة Base64 المنسوخة.
- `ANDROID_KEYSTORE_PASSWORD`: كلمة مرور ملف keystore.
- `ANDROID_KEY_ALIAS`: `smarthub-release`
- `ANDROID_KEY_PASSWORD`: كلمة مرور المفتاح (قد تكون نفس كلمة مرور keystore).

لا تضع القيم في Issues أو Pull Requests أو ملفات Git.

## 4) تشغيل الإصدار الموقّع

بعد إضافة الأسرار، افتح:
Actions → Android signed release → Run workflow

عند نجاح التشغيل سيظهر Artifact باسم `smarthub-ai-signed-release` ويحتوي على:
- `SmartHub-AI-release.apk`
- `SmartHub-AI-release.aab`

نزّل الملفات وافحصها قبل إرسالها إلى Uptodown أو أي متجر. لم يتم اختبار التطبيق على جهاز فعلي ضمن هذه العملية.

## تنبيه أمني

- لا تشارك ملف keystore أو كلمات مروره مع أي شخص.
- احتفظ بنسخة احتياطية مشفّرة من المفتاح.
- لا تنشئ مفتاحاً جديداً لكل إصدار؛ استخدم نفس المفتاح عند تحديث التطبيق.
