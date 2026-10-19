#!/usr/bin/env python3
"""One-time helper: turn a short-lived Facebook user token into a page token that does not expire.

  python3 poster/get_meta_token.py APP_ID APP_SECRET SHORT_LIVED_USER_TOKEN

Get SHORT_LIVED_USER_TOKEN from the Graph API Explorer (developers.facebook.com/tools/explorer)
with your app selected and these permissions: pages_show_list, pages_read_engagement,
pages_manage_posts, business_management, instagram_basic, instagram_content_publish.

Prints every Facebook Page you manage with its page id, a long-lived page token, and the linked
Instagram business account id. Paste the values into GitHub secrets (poster/SETUP.md).
"""
import json
import os
import sys
import urllib.parse
import urllib.request

GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v24.0')}"


def get(path, **params):
    return json.load(urllib.request.urlopen(f"{GRAPH}/{path}?" + urllib.parse.urlencode(params)))


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    app_id, app_secret, short = sys.argv[1:]
    long_user = get("oauth/access_token", grant_type="fb_exchange_token", client_id=app_id,
                    client_secret=app_secret, fb_exchange_token=short)["access_token"]
    pages = get("me/accounts", fields="id,name,access_token,instagram_business_account",
                access_token=long_user).get("data", [])
    if not pages:
        sys.exit("No pages found. Make sure you granted pages_show_list and chose your pages.")
    for p in pages:
        ig = (p.get("instagram_business_account") or {}).get("id", "(no Instagram linked)")
        print(f"\nPage: {p['name']}\n  page id:       {p['id']}\n  instagram id:  {ig}\n"
              f"  page token:    {p['access_token']}")
    print("\nThese page tokens come from a long-lived user token, so they don't expire "
          "unless you change your password or remove the app.")


if __name__ == "__main__":
    main()
