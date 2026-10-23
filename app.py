import os
import json
import html
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from datetime import datetime
from dotenv import load_dotenv

import streamlit as st
from datetime import timedelta

# Firebase Admin SDK imports
import firebase_admin
from firebase_admin import credentials, auth, firestore

load_dotenv()

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="ECO CARE",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS matching the ECO CARE Green Palette (Figma Design)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

    :root {
        font-family: 'Poppins', sans-serif;
        color: #1A1A1A;
    }
    html, body, [class*="css"], .stApp {
        font-family: 'Poppins', sans-serif;
    }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #F1F8F3;
        color: #1A1A1A;
    }
    [data-testid="stHeader"] {
        background-color: #F1F8F3;
    }
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] {
        padding-top: 1.75rem !important;
        padding-bottom: 1rem !important;
        margin-top: 0 !important;
        overflow: visible !important;
    }
    [data-testid="stSidebar"] {
        background-color: #0E2F24;
        min-width: 280px !important;
        max-width: 280px !important;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF;
    }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #C6D7CA;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        border-radius: 12px;
        padding: 8px 10px;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background-color: #1E5A3A;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label p {
        color: #FFFFFF;
    }
    [data-testid="stSidebar"] .stButton > button {
        color: #FFFFFF;
        background: #1E5A3A;
        border: 1px solid rgba(255,255,255,0.12);
    }
    .stApp {
        color: #1A1A1A;
    }
    [data-testid="stCaptionContainer"], .secondary-text {
        color: #5A6D5E;
    }
    [data-testid="stMain"] [data-testid="stWidgetLabel"],
    [data-testid="stMain"] [data-testid="stWidgetLabel"] *,
    [data-testid="stMain"] .stTextInput label,
    [data-testid="stMain"] .stSelectbox label,
    [data-testid="stMain"] .stCheckbox label,
    [data-testid="stMain"] .stRadio label,
    [data-testid="stMain"] .stFileUploader label {
        color: #263B32 !important;
        opacity: 1 !important;
    }
    [data-testid="stMain"] [data-testid="stCaptionContainer"],
    [data-testid="stMain"] [data-testid="stCaptionContainer"] * {
        color: #52665B !important;
        opacity: 1 !important;
    }
    [data-testid="stMain"] [data-baseweb="select"] *,
    [data-testid="stMain"] [data-testid="stTextInput"] input,
    [data-testid="stMain"] [data-testid="stTextArea"] textarea {
        color: #1A1A1A !important;
        opacity: 1 !important;
    }
    [data-testid="stMain"] input::placeholder,
    [data-testid="stMain"] textarea::placeholder {
        color: #68766F !important;
        opacity: 1 !important;
    }
    .metric-card {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 2px 12px rgba(14,47,36,0.06);
        border: 1px solid #E0E8E2;
        margin-bottom: 16px;
    }
    .card-title {
        font-size: 0.9rem;
        color: #5A6D5E;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .card-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1A1A1A;
    }
    .card-subtitle {
        font-size: 0.82rem;
        color: #5A6D5E;
    }
    .timeline-item {
        border-left: 2px solid #1E5A3A;
        padding-left: 14px;
        margin-bottom: 14px;
        position: relative;
    }
    .timeline-item::before {
        content: '';
        width: 10px;
        height: 10px;
        background-color: #1E5A3A;
        border-radius: 50%;
        position: absolute;
        left: -6px;
        top: 4px;
    }
    .timeline-time {
        font-size: 0.75rem;
        font-weight: 700;
        color: #1E5A3A;
    }
    .timeline-desc {
        font-size: 0.88rem;
        color: #1A1A1A;
        font-weight: 500;
    }
    .quick-chip {
        display: inline-block;
        background-color: #E8F5E9;
        color: #1E5A3A;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        margin: 4px;
    }
    .stButton > button, .stDownloadButton > button {
        color: #FFFFFF;
        background: #1E5A3A;
        border: 1px solid #1E5A3A;
        border-radius: 12px;
        font-family: 'Poppins', sans-serif;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        color: #FFFFFF;
        background: #16452D;
        border-color: #16452D;
    }
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
        color: #1A1A1A;
        background-color: #FFFFFF;
        border-color: #E0E8E2;
    }
    [data-testid="stChatMessage"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E8E2;
        border-radius: 16px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 2px 10px rgba(14,47,36,0.05);
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] * {
        color: #1A1A1A !important;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] a {
        color: #1E5A3A !important;
    }
    [data-testid="stImage"] img {
        object-fit: cover;
    }
    .hero-card {
        background: #FFFFFF;
        border: 1px solid #E0E8E2;
        border-radius: 20px;
        padding: 30px 34px;
        margin: 8px 0 22px;
        box-shadow: 0 2px 12px rgba(14,47,36,0.06);
    }
    .hero-eyebrow { color: #5A6D5E; font-size: 0.95rem; }
    .hero-heading { color: #1A1A1A; font-size: 1.8rem; font-weight: 700; margin: 6px 0; }
    .hero-copy { color: #5A6D5E; font-size: 1rem; margin: 0; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FIREBASE ADMIN & FIRESTORE INITIALIZATION
# ==========================================
FIREBASE_KEY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "serviceAccountKey.json"
)


def _load_firebase_credentials():
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path:
        if not os.path.isfile(credentials_path):
            raise FileNotFoundError(
                "GOOGLE_APPLICATION_CREDENTIALS points to a file that does not exist."
            )
        return credentials.Certificate(credentials_path)

    try:
        firebase_config = st.secrets.get("firebase")
    except FileNotFoundError:
        firebase_config = None

    if firebase_config:
        return credentials.Certificate(dict(firebase_config))

    if os.path.exists(FIREBASE_KEY_PATH):
        return credentials.Certificate(FIREBASE_KEY_PATH)

    st.error(
        "Firebase credentials are not configured. Add a service account key "
        "at 'serviceAccountKey.json', set GOOGLE_APPLICATION_CREDENTIALS to "
        "a service account JSON path, or configure the [firebase] section "
        "in Streamlit secrets."
    )
    st.stop()


if not firebase_admin._apps:
    firebase_admin.initialize_app(_load_firebase_credentials())

db = firestore.client()


def load_user_profile(email: str):
    """Load a user's saved profile or create their initial Firestore profile."""
    user_record = auth.get_user_by_email(email)
    user_ref = db.collection("users").document(user_record.uid)
    stored_profile = user_ref.get(
        field_paths=["name", "email", "location", "bio", "phone"]
    ).to_dict() or {}
    profile = {
        "name": stored_profile.get(
            "name", user_record.display_name or email.split("@", 1)[0]
        ),
        "email": stored_profile.get("email", email),
        "location": stored_profile.get("location", "Chennai, Tamil Nadu"),
        "bio": stored_profile.get("bio", ""),
        "phone": stored_profile.get("phone", ""),
        "online": True,
    }
    user_ref.set(
        {
            **{key: value for key, value in profile.items() if key != "online"},
            "avatar": firestore.DELETE_FIELD,
        },
        merge=True,
    )
    return user_record.uid, profile


def get_firebase_web_api_key():
    """Fetches Web API Key from environment or Streamlit secrets."""
    key = os.getenv("FIREBASE_WEB_API_KEY")
    if not key:
        try:
            key = st.secrets.get("FIREBASE_WEB_API_KEY")
        except Exception:
            key = None
    return key


def _firebase_auth_error(action, error):
    error_text = str(error).casefold()
    if "invalid_grant" in error_text or "invalid jwt signature" in error_text:
        return (
            f"{action}: Firebase rejected the service-account signing key. "
            "Download a new private key for the Firebase service account and "
            "replace the configured credentials. On Streamlit Cloud, update "
            "the [firebase] secret and reboot the app."
        )
    return f"{action}: {error}"


# ==========================================
# 3. AUTHENTICATION HELPER FUNCTIONS
# ==========================================
def verify_user_and_password(email: str, password: str):
    """
    1. Checks if email exists using Firebase Admin SDK.
    2. Verifies password using Firebase Auth REST API.
    """
    # Step 1: Check user existence using Admin SDK
    try:
        user_record = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        return False, "User not found, please signup"
    except Exception as e:
        return False, _firebase_auth_error("Account lookup error", e)

    # Step 2: Verify password via Firebase Auth REST API
    web_api_key = get_firebase_web_api_key()
    if not web_api_key:
        return False, "FIREBASE_WEB_API_KEY is not set. Please set it in .env or st.secrets to verify passwords."

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={web_api_key}"
    payload = json.dumps({"email": email, "password": password, "returnSecureToken": True}).encode("utf-8")
    req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            return True, data.get("email")
    except HTTPError as err:
        try:
            error_details = json.loads(err.read().decode("utf-8"))
            msg = error_details.get("error", {}).get("message", "")
        except Exception:
            msg = ""

        if msg in ["INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS"]:
            return False, "Invalid password"
        elif msg == "EMAIL_NOT_FOUND":
            return False, "User not found, please signup"
        elif msg == "USER_DISABLED":
            return False, "This user account has been disabled."
        return False, f"Authentication error: {msg or 'Please try again.'}"
    except (URLError, TimeoutError):
        return False, "Network error: Unable to reach authentication server."

def create_new_user(email: str, password: str):
    """Creates a new user using Firebase Admin SDK."""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    try:
        user = auth.create_user(email=email, password=password)
        return True, user.email
    except auth.EmailAlreadyExistsError:
        return False, "Email already exists. Please log in."
    except Exception as e:
        return False, _firebase_auth_error("Sign up failed", e)

def send_password_reset(email: str):
    """Generates password reset link using Firebase Admin SDK."""
    try:
        auth.get_user_by_email(email)
        link = auth.generate_password_reset_link(email)
        return True, link
    except auth.UserNotFoundError:
        return False, "User not found, please signup"
    except Exception as e:
        return False, _firebase_auth_error("Password reset failed", e)

# ==========================================
# 4. AUTHENTICATION GATE & LOGIN FLOW
# ==========================================
if "user" not in st.session_state:
    st.session_state["user"] = {
        "name": "Vasantha",
        "email": "vasanth@email.com",
        "location": "Chennai, Tamil Nadu",
        "bio": "",
        "phone": "",
        "online": True
    }

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_email"] = None

def open_profile_settings():
    user = st.session_state["user"]
    st.session_state["profile_name"] = user["name"]
    st.session_state["profile_email"] = user["email"]
    st.session_state["profile_location"] = user["location"]
    st.session_state["profile_bio"] = user.get("bio", "")
    st.session_state["profile_phone"] = user.get("phone", "")
    st.session_state["show_profile_dialog"] = True


def navigate_to_dashboard():
    st.session_state["navigation"] = "Dashboard"


@st.dialog("Profile settings")
def show_profile_dialog():
    user = st.session_state["user"]
    st.text_input("Full Name", key="profile_name")
    st.text_input("Email", key="profile_email")
    st.text_input("Location", key="profile_location")
    st.text_area("Bio / About", key="profile_bio", height=90)
    st.text_input("Phone Number", key="profile_phone")

    save_col, cancel_col = st.columns(2)
    with save_col:
        save_profile = st.button(
            "Save Changes",
            type="primary",
            use_container_width=True,
            key="save_profile"
        )
    with cancel_col:
        cancel_profile = st.button(
            "Cancel",
            use_container_width=True,
            key="cancel_profile"
        )

    if cancel_profile:
        st.session_state["show_profile_dialog"] = False
        st.rerun()

    if save_profile:
        name = st.session_state["profile_name"].strip()
        email = st.session_state["profile_email"].strip()
        if not name:
            st.error("Name cannot be empty.")
        elif "@" not in email:
            st.error("Enter a valid email address containing @.")
        else:
            location = st.session_state["profile_location"].strip()
            updated_user = {
                **{key: value for key, value in user.items() if key != "avatar"},
                "name": name,
                "email": email,
                "location": location,
                "bio": st.session_state["profile_bio"].strip(),
                "phone": st.session_state["profile_phone"].strip(),
            }
            try:
                user_ref = db.collection("users").document(st.session_state["user_uid"])
                user_ref.set(
                    {
                        **{key: value for key, value in updated_user.items() if key != "online"},
                        "avatar": firestore.DELETE_FIELD,
                    },
                    merge=True,
                )
            except Exception as error:
                st.error(f"Could not save your profile: {error}")
            else:
                st.session_state["user"] = updated_user
                location_parts = [part.strip() for part in location.split(",", 1)]
                from weather_module import ALL_STATES, STATES_DISTRICTS

                if len(location_parts) == 2 and location_parts[1] in ALL_STATES:
                    st.session_state["selected_state"] = location_parts[1]
                    st.session_state["weather_state_selector"] = location_parts[1]
                    districts = STATES_DISTRICTS.get(location_parts[1], [])
                    if location_parts[0] in districts:
                        st.session_state["selected_district"] = location_parts[0]
                        st.session_state["weather_dist_selector"] = location_parts[0]
                        st.session_state["custom_city_input"] = ""
                    else:
                        st.session_state["selected_district"] = districts[0] if districts else location_parts[0]
                        st.session_state["weather_dist_selector"] = st.session_state["selected_district"]
                        st.session_state["custom_city_input"] = location_parts[0]
                else:
                    st.session_state["custom_city_input"] = location_parts[0] if location_parts else ""
                if st.session_state.get("chat_messages"):
                    first_message = st.session_state.chat_messages[0]
                    if first_message["role"] == "assistant" and first_message["content"].startswith("Hello,"):
                        first_message["content"] = (
                            f"Hello, {name}! I'm here to help you every step of the way. "
                            "How can I assist your plants today?"
                        )
                st.session_state["show_profile_dialog"] = False
                st.session_state["profile_updated"] = True
                st.rerun()

if st.session_state.pop("profile_updated", False):
    st.toast("Profile updated successfully!", icon="✅")

# If user is NOT logged in, show ONLY authentication UI and stop execution
if not st.session_state["logged_in"]:
    st.markdown("""
    <style>
        body:has(.st-key-ec_auth_page) .stApp,
        body:has(.st-key-ec_auth_page) [data-testid="stAppViewContainer"],
        body:has(.st-key-ec_auth_page) [data-testid="stMain"],
        body:has(.st-key-ec_auth_page) [data-testid="stHeader"] {
            background: #FFFFFF !important;
        }
        body:has(.st-key-ec_auth_page) [data-testid="stSidebar"] {
            display: none;
        }
        body:has(.st-key-ec_auth_page) [data-testid="stMainBlockContainer"] {
            max-width: 560px !important;
            padding: 18px 28px 32px !important;
            margin: 0 auto !important;
        }
        .st-key-ec_auth_page {
            width: 100%;
        }
        .st-key-ec_auth_page [data-testid="stMarkdownContainer"] p {
            margin-bottom: 0;
        }
        .st-key-ec_auth_page [data-testid="stWidgetLabel"] label,
        .st-key-ec_auth_page [data-testid="stWidgetLabel"] p {
            color: #263B32 !important;
            font-size: 0.9rem !important;
            font-weight: 600 !important;
        }
        .st-key-ec_auth_page [data-testid="stTextInput"] input {
            min-height: 56px;
            border: 1px solid #D1D5DB;
            border-radius: 14px;
            padding: 0 14px;
            background: #FFFFFF;
        }
        .st-key-ec_auth_page [data-testid="stTextInput"] input:focus {
            border-color: #2E7D32;
            box-shadow: 0 0 0 1px #2E7D32;
        }
        .st-key-ec_auth_page [data-testid="stTextInput"] [data-testid="InputAdornment"] {
            color: #2E7D32;
        }
        .st-key-ec_auth_page .stButton > button {
            min-height: 54px;
            border-radius: 14px;
            font-weight: 600;
        }
        .st-key-ec_auth_page .st-key-auth_signup_footer .stButton > button,
        .st-key-ec_auth_page .st-key-auth_forgot .stButton > button {
            min-height: 32px;
            padding: 0;
            border: 0;
            background: transparent;
            color: #2E7D32;
            box-shadow: none;
        }
        .st-key-ec_auth_page .st-key-auth_signup_footer .stButton > button:hover,
        .st-key-ec_auth_page .st-key-auth_forgot .stButton > button:hover {
            color: #1B5E20;
            text-decoration: underline;
        }
        .st-key-ec_auth_page [data-testid="stCheckbox"] label {
            color: #475569 !important;
        }
        @media (max-width: 480px) {
            body:has(.st-key-ec_auth_page) [data-testid="stMainBlockContainer"] {
                padding: 12px 24px 28px !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    if "auth_view" not in st.session_state:
        st.session_state["auth_view"] = "login"
    if "show_password_reset" not in st.session_state:
        st.session_state["show_password_reset"] = False

    with st.container(key="ec_auth_page"):
        if st.session_state["auth_view"] == "login":
            st.markdown("""
            <div style="margin-top:34px;">
                <p style="color:#2E7D32;font-size:1.15rem;font-weight:600;">Welcome Back</p>
                <h1 style="color:#0F172A;font-size:clamp(2.25rem,8vw,2.8rem);"
                    >Login to Eco Care</h1>
                <p style="color:#64748B;font-size:1rem;line-height:1.55;margin-top:10px;">
                    Enter your credentials to access your account and continue making a difference.
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.write("")
            email_input = st.text_input(
                "Email Address",
                placeholder="Enter your email address",
                value=st.session_state.get("remembered_email", ""),
                key="tab_login_email",
                icon=":material/mail:",
            )
            password_input = st.text_input(
                "Password",
                placeholder="Enter your password",
                type="password",
                key="tab_login_password",
                icon=":material/lock:",
            )

            remember_col, forgot_col = st.columns([1, 1], vertical_alignment="center")
            with remember_col:
                remember_username = st.checkbox("Remember me", key="remember_me")
            with forgot_col:
                if st.button("Forgot password?", key="auth_forgot"):
                    st.session_state["show_password_reset"] = not st.session_state[
                        "show_password_reset"
                    ]

            if st.session_state["show_password_reset"]:
                reset_email = st.text_input(
                    "Enter registered email",
                    placeholder="Enter your email address",
                    key="pwd_reset_email",
                    icon=":material/mail:",
                )
                if st.button("Send Reset Link", key="btn_reset"):
                    if reset_email.strip():
                        success, result = send_password_reset(reset_email.strip())
                        if success:
                            st.success("Password reset link generated:")
                            st.info(result)
                        else:
                            st.error(result)
                    else:
                        st.warning("Please enter your email.")

            if st.button("Login  →", type="primary", use_container_width=True, key="btn_signin"):
                if not email_input.strip() or not password_input:
                    st.error("Please enter both email and password.")
                else:
                    success, message = verify_user_and_password(email_input.strip(), password_input)
                    if success:
                        try:
                            user_uid, profile = load_user_profile(message or email_input.strip())
                        except Exception as error:
                            st.error(f"Could not load your saved profile: {error}")
                        else:
                            st.session_state["user_uid"] = user_uid
                            st.session_state["user"] = profile
                            st.session_state["logged_in"] = True
                            st.session_state["user_email"] = message
                            if remember_username:
                                st.session_state["remembered_email"] = email_input.strip()
                            else:
                                st.session_state.pop("remembered_email", None)
                            st.success("Signed in successfully! Loading dashboard...")
                            st.rerun()
                    else:
                        st.error(message)

            st.write("")
            footer_copy, footer_link = st.columns([1, 1.25], vertical_alignment="center")
            with footer_copy:
                st.markdown(
                    "<p style='text-align:right;color:#64748B;font-size:0.88rem;"
                    "white-space:nowrap;'>New to Eco Care?</p>",
                    unsafe_allow_html=True,
                )
            with footer_link:
                if st.button("Create an account →", key="auth_signup_footer"):
                    st.session_state["auth_view"] = "signup"
                    st.rerun()
        else:
            st.markdown("""
            <div style="margin-top:34px;">
                <p style="color:#2E7D32;font-size:1.15rem;font-weight:600;">Join Eco Care</p>
                <h1 style="color:#0F172A;font-size:2.5rem;">Create an account</h1>
                <p style="color:#64748B;font-size:1rem;line-height:1.55;margin-top:10px;">
                    Create your account to care for your plants and make a difference.
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.write("")
            signup_email = st.text_input(
                "Email Address",
                placeholder="Enter your email address",
                key="tab_signup_email",
                icon=":material/mail:",
            )
            signup_pass = st.text_input(
                "Password (min 6 characters)",
                type="password",
                placeholder="Create a password",
                key="tab_signup_password",
                icon=":material/lock:",
            )
            signup_pass_confirm = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Enter your password again",
                key="tab_signup_confirm",
                icon=":material/lock:",
            )

            if st.button("Create Account  →", type="primary", use_container_width=True, key="btn_signup"):
                if not signup_email.strip() or not signup_pass or not signup_pass_confirm:
                    st.error("Please fill in all fields.")
                elif len(signup_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                elif signup_pass != signup_pass_confirm:
                    st.error("Passwords do not match.")
                else:
                    success, message = create_new_user(signup_email.strip(), signup_pass)
                    if success:
                        st.success(f"Account created successfully for {message}!")
                        st.info("You can now log in with your new account.")
                        st.session_state["auth_view"] = "login"
                    else:
                        st.error(message)

            st.write("")
            login_copy, login_link = st.columns([1, 1.1], vertical_alignment="center")
            with login_copy:
                st.markdown(
                    "<p style='text-align:right;color:#64748B;font-size:0.88rem;"
                    "white-space:nowrap;'>Already have an account?</p>",
                    unsafe_allow_html=True,
                )
            with login_link:
                if st.button("Log in →", key="auth_signup_footer"):
                    st.session_state["auth_view"] = "login"
                    st.rerun()

    # STOP execution here so dashboard only renders when logged_in is True
    st.stop()


# ==========================================
# 5. FIRESTORE LOGGING & GEMINI SETUP
# ==========================================
def save_chat_to_firestore(user_query: str, bot_response: str, has_image: bool = False):
    """Logs conversation history to Firebase Firestore."""
    if db:
        try:
            db.collection("chat_history").add({
                "timestamp": firestore.SERVER_TIMESTAMP,
                "user_query": user_query,
                "bot_response": bot_response,
                "has_image": has_image,
                "user": st.session_state.get("user_email", "Alex")
            })
        except Exception as e:
            st.sidebar.warning(f"Firestore Sync Warning: {e}")

SYSTEM_PROMPT = """
You are "ECO CARE Assistant" (the AI Botanist inside ECO CARE), an intelligent assistant specialized in urban plant care. 
Your core purpose is to help urban dwellers maintain healthy indoor, balcony, and terrace plants.

Expert Domain Knowledge:
1. Plant species identification and classification.
2. Urban environmental challenges (limited sunlight, dry indoor AC/heater air, urban pollution/dust, balcony draft).
3. Care guidelines covering precise watering schedules, optimal sunlight levels, soil quality, and fertilization.
4. Pest identification, disease management, and treating yellowing or drooping leaves.

Behavior Guidelines:
- If an image is provided:
  * Identify plant name (Common + Botanical).
  * Diagnose leaf/stem health, pests, or stress symptoms.
  * Provide an immediate, realistic action step for busy urban schedules.
  * Provide light, watering, and soil maintenance recommendations.
  * Organize the response with a short identification line, concise labeled facts
    (plant name, type, ideal temperature if known, light, and common issues), then
    a separate "Care Tips" heading with practical bullets.
  * Be clear when an identification or diagnosis is uncertain; do not invent facts.
- Keep your answers structured, encouraging, clear, and practical.
"""

@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key):
    from google import genai
    from google.genai import types

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=2,
                initial_delay=0.5,
                max_delay=2,
                jitter=0,
            )
        ),
    )


def stream_gemini_response(content):
    """Stream a plant-care response from Gemini as text chunks arrive."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY")
        except FileNotFoundError:
            api_key = None
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    from google.genai import types

    gemini_client = get_gemini_client(api_key)
    has_text = False
    try:
        stream = gemini_client.models.generate_content_stream(
            model="gemini-3.8-flash",
            contents=content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            ),
        )
        for chunk in stream:
            text = chunk.text
            if text:
                has_text = True
                yield text
    except Exception as error:
        status = str(
            getattr(error, "status", "")
            or getattr(error, "code", "")
        ).upper()
        message = str(error).upper()
        streaming_unavailable = (
            status in {"404", "405", "501", "UNIMPLEMENTED"}
            or any(
                marker in message
                for marker in (
                    "404",
                    "405",
                    "501",
                    "UNIMPLEMENTED",
                    "STREAMING NOT SUPPORTED",
                )
            )
        )
        if streaming_unavailable and not has_text:
            response = gemini_client.models.generate_content(
                model="gemini-3.8-flash",
                contents=content,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT
                ),
            )
            if response.text and response.text.strip():
                yield response.text
                return
            raise RuntimeError(
                "Gemini returned an empty response. Please try again."
            ) from error

        is_overloaded = (
            status in {"503", "UNAVAILABLE"}
            or "503" in message
            or "UNAVAILABLE" in message
        )
        is_invalid_api_key = (
            status in {"401", "UNAUTHENTICATED"}
            or "ACCESS_TOKEN_TYPE_UNSUPPORTED" in message
            or "API KEY NOT VALID" in message
        )
        if is_overloaded:
            raise RuntimeError(
                "Gemini 3.8 Flash is busy. Please wait a moment and try again."
            ) from error
        if is_invalid_api_key:
            raise RuntimeError(
                "Google rejected the configured Gemini API key. Create or "
                "copy a valid Gemini API key from Google AI Studio, then "
                "update GEMINI_API_KEY in the local .env file or Streamlit "
                "Cloud secrets and restart the app. Make sure the key is "
                "for the Generative Language API, not an OAuth access token."
            ) from error
        raise

    if not has_text:
        raise RuntimeError(
            "Gemini returned an empty response. Please rephrase your question and try again."
        )


# ==========================================
# 6. SIDEBAR NAVIGATION (When Logged In)
# ==========================================
with st.sidebar:
    st.markdown("## 🌿 **ECO CARE**")
    st.caption("Urban Plant Care Intelligence")

    nav_option = st.radio(
        "Navigation",
        ["Dashboard", "Weather Monitoring", "Chat Assistant"],
        index=0,
        key="navigation",
        label_visibility="collapsed"
    )
    previous_navigation = st.session_state.get("active_navigation")
    if previous_navigation is not None and previous_navigation != nav_option:
        st.session_state["show_profile_dialog"] = False
    st.session_state["active_navigation"] = nav_option

    st.divider()

    user = st.session_state["user"]
    profile_cols = st.columns([4, 1])
    with profile_cols[0]:
        if st.button(user["name"], use_container_width=True, key="sidebar_profile"):
            open_profile_settings()
            st.rerun()
        st.caption("Online")
    with profile_cols[1]:
        if st.button("✎", help="Edit profile", key="sidebar_edit_profile"):
            open_profile_settings()
            st.rerun()

    # Logout Button
    if st.button("Log out", use_container_width=True, key="logout"):
        st.session_state["logged_in"] = False
        st.session_state["user_email"] = None
        st.session_state["user_uid"] = None
        if not st.session_state.get("remembered_email"):
            st.session_state.pop("tab_login_email", None)
        st.rerun()

if st.session_state.get("show_profile_dialog", False):
    show_profile_dialog()


# ==========================================
# 7. VIEW: DASHBOARD
# ==========================================
if nav_option == "Dashboard":
    from dashboard import render_dashboard

    st.session_state["ecocare_firestore"] = db
    render_dashboard()


# ==========================================
# 8. VIEW: WEATHER MONITORING
# ==========================================
elif nav_option == "Weather Monitoring":
    from weather_module import weather_monitoring_page

    st.session_state["ecocare_firestore"] = db
    weather_monitoring_page()


# ==========================================
# 9. VIEW: CHAT ASSISTANT
# ==========================================
elif nav_option == "Chat Assistant":
    from PIL import Image

    user_name = html.escape(st.session_state["user"]["name"])
    st.markdown(
        """
        <style>
        .eco-chat-header {
            display:flex; align-items:center; gap:14px; margin:0 0 18px;
            padding:18px 22px; border-radius:18px;
            background:linear-gradient(120deg,#2e7d32,#1e5a3a); color:#fff;
            box-shadow:0 5px 18px #1d5c3022;
        }
        .eco-chat-header .eco-chat-logo {
            width:48px;height:48px;flex:none;border-radius:50%;
            display:grid;place-items:center;background:#ffffff25;font-size:26px;
        }
        .eco-chat-header h1 {margin:0;color:#fff;font-size:21px;font-weight:700}
        .eco-chat-header p {margin:3px 0 0;color:#e7f4e9;font-size:12px}
        .eco-chat-header time {margin-left:auto;align-self:flex-start;font-size:12px;color:#e7f4e9}
        [data-testid="stChatMessage"] {
            width:fit-content;max-width:88%;padding:13px 16px;margin-bottom:12px;
            border:1px solid #e4eee7;border-radius:20px;background:#fff;
            box-shadow:0 3px 12px #173b2410;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            margin-left:auto;background:#e8f5e9;border-color:#d6ebd9;
            border-bottom-right-radius:6px;flex-direction:row-reverse;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            margin-right:auto;border-bottom-left-radius:6px;
        }
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] * {
            color:#26352c!important;font-size:14px;line-height:1.55;
        }
        [data-testid="stChatMessage"] [data-testid="stCaptionContainer"] {
            text-align:right;color:#718078!important;font-size:10px;
        }
        div[class*="st-key-chat_send_photo"] button,
        div[class*="st-key-chat_identify_plant"] button,
        div[class*="st-key-chat_detect_disease"] button,
        div[class*="st-key-chat_watering_schedule"] button,
        div[class*="st-key-chat_plant_library"] button {
            min-height:40px;padding:6px 8px;border:1px solid #a5d6a7;
            border-radius:999px;background:#e8f5e9;color:#2e7d32;
            font-size:11px;font-weight:600;white-space:nowrap;
        }
        div[class*="st-key-chat_send_photo"] button:hover,
        div[class*="st-key-chat_identify_plant"] button:hover,
        div[class*="st-key-chat_detect_disease"] button:hover,
        div[class*="st-key-chat_watering_schedule"] button:hover,
        div[class*="st-key-chat_plant_library"] button:hover {
            color:#1b5e20;background:#d7efda;border-color:#66bb6a;
        }
        [data-testid="stChatInput"] {
            border:1px solid #d7e5dc;border-radius:18px;background:#fff;
            box-shadow:0 3px 16px #173b2410;
        }
        [data-testid="stChatInput"] textarea {background:transparent!important}
        div[class*="st-key-chat_back_dashboard"] button {
            min-height:84px;background:#2e7d32;color:#fff;border:0;
            border-radius:16px 0 0 16px;font-size:30px;
        }
        @media(max-width:600px) {
            [data-testid="stMainBlockContainer"],
            [data-testid="stAppViewBlockContainer"] {padding:10px 10px 5rem!important}
            .eco-chat-header {gap:10px;padding:14px 13px;border-radius:0 0 16px 16px;margin:-10px -10px 14px}
            .eco-chat-header .eco-chat-logo {width:42px;height:42px;font-size:23px}
            .eco-chat-header h1 {font-size:18px}
            .eco-chat-header p {font-size:10px}
            div[class*="st-key-chat_back_dashboard"] button {min-height:78px}
            [data-testid="stChatMessage"] {max-width:94%;padding:10px 12px}
            div[class*="st-key-chat_send_photo"] button,
            div[class*="st-key-chat_identify_plant"] button,
            div[class*="st-key-chat_detect_disease"] button,
            div[class*="st-key-chat_watering_schedule"] button,
            div[class*="st-key-chat_plant_library"] button {
                min-height:44px;font-size:9px;padding:5px 3px;white-space:normal;line-height:1.1
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    back_col, header_col = st.columns([0.55, 9.45], gap="small")
    with back_col:
        st.button(
            "‹",
            key="chat_back_dashboard",
            help="Back to dashboard",
            use_container_width=True,
            on_click=navigate_to_dashboard,
        )
    with header_col:
        st.markdown(
            f"""
            <header class="eco-chat-header">
                <div class="eco-chat-logo">🌿</div>
                <div>
                    <h1>Eco Care Chatbot</h1>
                    <p>Ask anything about your plants! (Identify • Detect • Care)</p>
                </div>
                <time>{datetime.now().strftime("%I:%M").lstrip("0")}</time>
            </header>
            """,
            unsafe_allow_html=True,
        )

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": f"Hello, {user_name}! I'm here to help with plant identification, disease detection, and everyday care. What would you like to know?",
                "timestamp": datetime.now().strftime("%I:%M %p"),
            }
        ]
    for message in st.session_state.chat_messages:
        message.setdefault("timestamp", datetime.now().strftime("%I:%M %p"))

    preset_prompt = None
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"], avatar="🌿" if msg["role"] == "assistant" else "👤"):
            if "image" in msg:
                st.image(msg["image"], width=280)
            st.markdown(msg["content"])
            st.caption(msg["timestamp"])

    photo_col, identify_col, disease_col, watering_col, library_col = st.columns(5, gap="small")
    with photo_col:
        if st.button("📷 Send Photo", key="chat_send_photo", use_container_width=True):
            st.session_state["show_chat_photo_upload"] = True
    with identify_col:
        if st.button("🌿 Identify Plant", key="chat_identify_plant", use_container_width=True):
            preset_prompt = "Help me identify a plant and explain its key care needs."
    with disease_col:
        if st.button("⌕ Detect Disease", key="chat_detect_disease", use_container_width=True):
            preset_prompt = "Look for signs of disease or pests in my plant and suggest safe next steps."
    with watering_col:
        if st.button("💧 Watering Schedule", key="chat_watering_schedule", use_container_width=True):
            preset_prompt = "Help me create a practical watering schedule for my plants."
    with library_col:
        if st.button("▤ Plant Library", key="chat_plant_library", use_container_width=True):
            preset_prompt = "Recommend plants from the Eco Care plant library for an urban home."

    uploaded_image = None
    if st.session_state.get("show_chat_photo_upload", False):
        upload_col, cancel_col = st.columns([5, 1])
        with upload_col:
            upload_key = f"chat_photo_upload_{st.session_state.get('chat_photo_upload_version', 0)}"
            uploaded_image = st.file_uploader(
                "Choose a plant photo",
                type=["jpg", "jpeg", "png"],
                key=upload_key,
            )
        with cancel_col:
            if st.button("✕", key="chat_cancel_photo", help="Close photo upload"):
                st.session_state["show_chat_photo_upload"] = False
                st.rerun()

    user_input = st.chat_input("Ask a question about your plants...") or preset_prompt

    if user_input or uploaded_image:
        display_text = user_input if user_input else "Please identify this plant and analyze its health."
        
        pil_img = None
        if uploaded_image:
            pil_img = Image.open(uploaded_image)
            pil_img.thumbnail((1280, 1280))

        # Record user message in UI
        timestamp = datetime.now().strftime("%I:%M %p")
        user_msg_record = {"role": "user", "content": display_text, "timestamp": timestamp}
        if pil_img:
            user_msg_record["image"] = pil_img
        st.session_state.chat_messages.append(user_msg_record)

        with st.chat_message("user", avatar="👤"):
            if pil_img:
                st.image(pil_img, width=280)
            st.markdown(display_text)
            st.caption(timestamp)

        with st.chat_message("assistant", avatar="🌿"):
            response_placeholder = st.empty()
            response_placeholder.markdown("_Thinking..._")
            try:
                contents = [display_text, pil_img] if pil_img else display_text
                bot_reply = response_placeholder.write_stream(
                    stream_gemini_response(contents)
                )
                reply_timestamp = datetime.now().strftime("%I:%M %p")
                st.caption(reply_timestamp)

                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": bot_reply,
                    "timestamp": reply_timestamp,
                })
                save_chat_to_firestore(display_text, bot_reply, has_image=(pil_img is not None))
            except Exception as err:
                error_message = f"I couldn't get a response from Gemini: {err}"
                reply_timestamp = datetime.now().strftime("%I:%M %p")
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": error_message,
                    "timestamp": reply_timestamp,
                })
                response_placeholder.error(error_message)
        if uploaded_image:
            st.session_state["show_chat_photo_upload"] = False
            st.session_state["chat_photo_upload_version"] = (
                st.session_state.get("chat_photo_upload_version", 0) + 1
            )
