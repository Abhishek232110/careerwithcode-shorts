# Direct posting setup (no Zapier, no Metricool)

Claude already makes the shorts. After this one-time setup, a GitHub Action in your
`careerwithcode-shorts` repo uploads each short straight to YouTube, Facebook and Instagram
through their official APIs. Everything here works in a browser; no terminal is needed.
On a phone, switch Chrome to "Desktop site" for the Google Cloud, Meta and GitHub pages.

You end up adding up to **10 GitHub secrets**. Each part can be done on its own, and anything
missing is simply skipped, so you can start with Facebook (fastest) and add the rest later.

Where secrets go: <https://github.com/Abhishek232110/careerwithcode-shorts/settings/secrets/actions>
→ **New repository secret** → paste the name and value exactly.

---

## Part 1: YouTube (do it twice, once per channel, about 15 minutes each)

Do each channel signed in with the Google account that owns it
(CuriosityBox: `abhi7392067649@gmail.com`; CareerWithCode: its own Gmail).

1. Open <https://console.cloud.google.com/projectcreate>, name it (for example
   `curiositybox-poster`) and click **Create**. Make sure the new project is selected at the top.
2. Open <https://console.cloud.google.com/apis/library/youtube.googleapis.com> and click **Enable**.
3. Open <https://console.cloud.google.com/auth/overview> → **Get started**: app name
   `Shorts poster`, your email, audience **External**, your email again, agree, **Create**.
4. Open <https://console.cloud.google.com/auth/audience> → **Publish app** → confirm.
   The status must say **In production**. If it stays "Testing", the login expires after
   7 days and posting stops.
5. Open <https://console.cloud.google.com/auth/clients> → **Create client**:
   - Application type: **Web application**
   - Authorized redirect URIs → **Add URI**: `https://developers.google.com/oauthplayground`
   - **Create**, then copy the **Client ID** and **Client secret**.
6. Open the OAuth Playground: <https://developers.google.com/oauthplayground>
   - Click the gear icon (top right) → tick **Use your own OAuth credentials** → paste the
     Client ID and Client secret → close.
   - In "Input your own scopes" (left, bottom) paste:
     `https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly`
   - **Authorize APIs** → sign in → pick the right channel → "Google hasn't verified this app"
     → **Advanced → Go to Shorts poster (unsafe)** → **Continue**.
   - Click **Exchange authorization code for tokens** and copy the **Refresh token**.
7. Add three secrets:

   | Channel        | Secret names |
   |----------------|--------------|
   | CuriosityBox   | `CB_YT_CLIENT_ID`, `CB_YT_CLIENT_SECRET`, `CB_YT_REFRESH_TOKEN` |
   | CareerWithCode | `CWC_YT_CLIENT_ID`, `CWC_YT_CLIENT_SECRET`, `CWC_YT_REFRESH_TOKEN` |

8. **Important: the YouTube audit.** Google locks videos uploaded by a new API project to
   **private** until the project passes an audit. Submit
   <https://support.google.com/youtube/contact/yt_api_form> for each project ("internal tool
   that uploads my own channel's Shorts"). Approval can take days or weeks. Until then each
   short is uploaded as private, and you would have to make it public in YouTube Studio by hand.

## Part 2: Facebook pages and Instagram (one time, about 15 minutes)

You must be an admin of both pages. For Instagram, the CareerWithCode Instagram must be a
Professional account linked to the CareerWithCode Facebook page.

1. Open <https://developers.facebook.com/apps> → **Create app** → name `Shorts poster` →
   choose the use cases for managing a Page and for Instagram content publishing → create.
   You can leave it in Development mode.
2. Open the Graph API Explorer: <https://developers.facebook.com/tools/explorer>
   - Meta App: pick `Shorts poster`. User or Page: **Get User Access Token**.
   - Add permissions: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`,
     `business_management`, `instagram_basic`, `instagram_content_publish`
   - **Generate Access Token** → allow both pages (and the Instagram account).
3. Copy that token, open <https://developers.facebook.com/tools/debug/accesstoken>, paste it,
   **Debug** → **Extend Access Token** at the bottom → copy the long-lived token.
4. Back in the Graph API Explorer, paste the long-lived token into the Access Token box, put
   this in the query box and click **Submit**:
   `me/accounts?fields=id,name,access_token,instagram_business_account`
   Each page in the result has `id`, `access_token` (this page token does not expire) and,
   if linked, `instagram_business_account.id`.
5. Add secrets:

   | Secret name | Value |
   |---|---|
   | `CB_FB_PAGE_TOKEN` | `access_token` of CuriosityBox Hindi Facts & Stories |
   | `CWC_FB_PAGE_ID` | `id` of the CareerWithCode page |
   | `CWC_FB_PAGE_TOKEN` | `access_token` of the CareerWithCode page |
   | `CWC_IG_USER_ID` | `instagram_business_account.id` of the CareerWithCode page |

## Part 3: Tell Claude

Say "secrets added" in the project. Claude then runs the built-in check (which shows `ready` or
`missing` for every channel and platform without posting anything), switches the four daily
shorts to direct posting, posts a test short, and sends you the links.
