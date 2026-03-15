"""Login form presets for common applications."""

PRESETS = {
    "wordpress": {
        "login_path": "/wp-login.php",
        "method": "POST",
        "username_field": "log",
        "password_field": "pwd",
        "extra_fields": {
            "wp-submit": "Log In",
            "redirect_to": "",
            "testcookie": "1",
        },
        "fail_string": "is incorrect",
        "cookies": {"wordpress_test_cookie": "WP+Cookie+check"},
        "description": "WordPress wp-login.php brute force",
    },
    "jenkins": {
        "login_path": "/j_spring_security_check",
        "method": "POST",
        "username_field": "j_username",
        "password_field": "j_password",
        "extra_fields": {
            "from": "/",
            "Submit": "Sign in",
        },
        "fail_string": "loginError",
        "cookies": {},
        "description": "Jenkins Spring Security brute force",
    },
    "drupal": {
        "login_path": "/user/login",
        "method": "POST",
        "username_field": "name",
        "password_field": "pass",
        "extra_fields": {
            "form_id": "user_login_form",
            "op": "Log in",
        },
        "fail_string": "Unrecognized username or password",
        "cookies": {},
        "description": "Drupal user login brute force",
    },
    "joomla": {
        "login_path": "/administrator/index.php",
        "method": "POST",
        "username_field": "username",
        "password_field": "passwd",
        "extra_fields": {
            "option": "com_login",
            "task": "login",
        },
        "fail_string": "Username and password do not match",
        "cookies": {},
        "description": "Joomla administrator brute force",
    },
}

WORDLIST_PATHS = {
    "rockyou": "/usr/share/wordlists/rockyou.txt",
    "common": "/usr/share/seclists/Passwords/Common-Credentials/10k-most-common.txt",
    "top100": "/usr/share/seclists/Passwords/Common-Credentials/top-100.txt",
    "top1000": "/usr/share/seclists/Passwords/Common-Credentials/top-1000.txt",
    "default": "/usr/share/seclists/Passwords/Default-Credentials/default-passwords.txt",
}


def resolve_wordlist(name_or_path: str) -> str:
    """Resolve a wordlist name to a file path."""
    if name_or_path in WORDLIST_PATHS:
        return WORDLIST_PATHS[name_or_path]
    return name_or_path
