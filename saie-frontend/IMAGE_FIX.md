# SAIE — Image Bug Fix Documentation

## Problem

All images on the live website were broken (not loading). The issue was reported after the project was handed over to a new team member.

---

## Root Cause Analysis

### Cause 1 — Missing Production Environment File (Main Culprit)

Next.js only reads `.env` files from **inside** the `saie-frontend/` folder. The team had a reference file called `saie-frontend.env` sitting at the **project root**, which Next.js never loads.

This means in production, `NEXT_PUBLIC_AWS_URL` was `undefined`. All homepage images fell back to the localhost URL (`http://localhost:8000/...`) which does not exist on the live server — breaking every image.

The platform (Vercel/DigitalOcean) likely had these env vars manually entered at some point, which is why images worked before. Once those were cleared or reset, everything broke.

### Cause 2 — Wrong S3 Region in the Env Var

The `saie-frontend.env` reference file had:

```
NEXT_PUBLIC_AWS_URL=https://saie-media.s3.amazonaws.com
```

The S3 bucket is in region `eu-north-1`, so the correct URL is:

```
NEXT_PUBLIC_AWS_URL=https://saie-media.s3.eu-north-1.amazonaws.com
```

AWS S3 buckets outside `us-east-1` require the region in the URL. Without it, requests fail or get silently rejected.

### Cause 3 — `next.config.js` Was Empty

Next.js blocks external images in `<Image>` components by default. The config had no `remotePatterns` set, which would block any `next/image` usage loading from S3 or the API domain.

### Cause 4 — Wrong Localhost Fallback in `page.tsx`

The homepage fallback URL had a stray `/api` suffix:

```js
// Before (wrong)
const API_URL = process.env.NEXT_PUBLIC_AWS_URL || "http://localhost:8000/api";
// Images would resolve to: http://localhost:8000/api/media/home/1.webp ❌

// After (correct)
const API_URL = process.env.NEXT_PUBLIC_AWS_URL || "http://localhost:8000";
// Images resolve to: http://localhost:8000/media/home/1.webp ✅
```

---

## Files Changed

### 1. `saie-frontend/.env.production` — CREATED

Created this file so Next.js automatically loads production variables during build.

```env
NEXT_PUBLIC_API_URL=https://api.saie-clips.com/api
NEXT_PUBLIC_AWS_URL=https://saie-media.s3.eu-north-1.amazonaws.com
NEXT_PUBLIC_SITE_URL=https://saie-clips.com
NEXT_PUBLIC_RAPIDAPI_KEY=<your_rapidapi_key>
```

### 2. `saie-frontend.env` — UPDATED

Fixed the S3 URL to include the region.

```diff
- NEXT_PUBLIC_AWS_URL=https://saie-media.s3.amazonaws.com
+ NEXT_PUBLIC_AWS_URL=https://saie-media.s3.eu-north-1.amazonaws.com
```

### 3. `saie-frontend/next.config.js` — UPDATED

Added `remotePatterns` to allow external images from S3 and the API.

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "saie-media.s3.eu-north-1.amazonaws.com",
      },
      {
        protocol: "https",
        hostname: "api.saie-clips.com",
      },
    ],
  },
};

module.exports = nextConfig;
```

### 4. `saie-frontend/app/(client)/page.tsx` — UPDATED

Fixed the localhost fallback URL (removed stray `/api`).

```diff
- const API_URL = process.env.NEXT_PUBLIC_AWS_URL || "http://localhost:8000/api";
+ const API_URL = process.env.NEXT_PUBLIC_AWS_URL || "http://localhost:8000";
```

---

## How to Deploy the Fix Live

### Hosting Architecture

| Component | Platform | URL |
|---|---|---|
| **Frontend** | Vercel | `saie.vercel.app` → `saie-clips.com` |
| **Backend** | Render.com | `ecommerce-backend-dvho.onrender.com` → `api.saie-clips.com` |
| **Database** | DigitalOcean PostgreSQL | — |
| **File Storage** | AWS S3 (eu-north-1) | `saie-media` bucket |
| **DNS/CDN** | Cloudflare | Proxying both domains |

---

### Fix on Vercel (Frontend)

This is the primary fix for broken images.

1. Go to [vercel.com](https://vercel.com) and log in
2. Click on your **SAIE** project
3. Navigate to **Settings → Environment Variables**
4. Add or update these variables for **Production**:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://api.saie-clips.com/api` |
   | `NEXT_PUBLIC_AWS_URL` | `https://saie-media.s3.eu-north-1.amazonaws.com` |
   | `NEXT_PUBLIC_SITE_URL` | `https://saie-clips.com` |
   | `NEXT_PUBLIC_RAPIDAPI_KEY` | `d17c12514fmsh84c03149daf2e13p17434ejsn792d6389cfda` |

5. Click **Save** — Vercel will auto-redeploy your frontend
6. Go to **Deployments** tab and wait for the new build to complete (~2-3 minutes)

Once redeployed, images should load immediately.

---

### Optional: Update Backend (Render.com)

The backend should already have correct env vars, but if needed:

1. Go to [render.com](https://render.com) and log in
2. Click the **SAIE backend** service
3. Go to **Environment** tab
4. Verify these are set:
   - `USE_S3=True`
   - `AWS_S3_REGION_NAME=eu-north-1`
   - `AWS_STORAGE_BUCKET_NAME=saie-media`

No changes needed here unless they're missing.

---

## Summary of Files Changed (for reference)

| File | Change | Location |
|---|---|---|
| `.env.production` | **Created** | `saie-frontend/.env.production` |
| `saie-frontend.env` | S3 URL region added | project root |
| `next.config.js` | Added `images.remotePatterns` | `saie-frontend/next.config.js` |
| `page.tsx` | Fixed localhost fallback | `saie-frontend/app/(client)/page.tsx` |

---

## Quick Reference — Env File Locations

| File | Loaded by Next.js? | Purpose |
|---|---|---|
| `saie-frontend/.env.local` | Yes (dev only) | Local development vars |
| `saie-frontend/.env.production` | Yes (production builds) | Production vars — **created in this fix** |
| `saie-frontend.env` (project root) | **No** | Reference/backup only — never auto-loaded |

---

---

## Status Update (After Fix Applied)

### ✅ Completed on DigitalOcean Droplet

1. Updated `/var/www/saie-frontend/.env`
   - Changed `NEXT_PUBLIC_AWS_URL=https://saie-media.s3.amazonaws.com`
   - To: `NEXT_PUBLIC_AWS_URL=https://saie-media.s3.eu-north-1.amazonaws.com`
2. Ran `npm run build` — Built successfully
3. Ran `pm2 restart saie-frontend` — Restarted successfully

### 🚧 Issue Found After Fix

Images are now trying to load from the **correct S3 URL**, but AWS S3 is returning **403 Forbidden**.

This means the S3 bucket has **public access blocked**.

---

## Next Step — AWS S3 Configuration

The developer needs to **enable public read access** on the S3 bucket.

### Option 1 — Allow Public Access (Recommended for public images)

Go to **AWS Console → S3 → saie-media bucket**:

1. **Permissions tab → Block public access settings**
   - Uncheck all 4 "Block public access" options
   - Click Save

2. **Bucket Policy** → Add this policy:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "PublicReadGetObject",
         "Effect": "Allow",
         "Principal": "*",
         "Action": "s3:GetObject",
         "Resource": "arn:aws:s3:::saie-media/*"
       }
     ]
   }
   ```

3. **Confirm and Save**

### Option 2 — Use CloudFront Distribution (More secure)

Instead of public S3 access, use CloudFront CDN to serve images securely. This requires configuring a CloudFront distribution pointing to the S3 bucket.

---

## Summary

Images broke because:
1. ❌ Frontend env var was missing S3 region (`eu-north-1`)
2. ❌ S3 bucket public access was blocked

**Fixed:**
1. ✅ Updated env var with correct region
2. ✅ Rebuilt and restarted frontend

**Remaining:**
- 🔄 Developer must enable S3 public read access in AWS console

Once the developer does that, all images will load immediately.
