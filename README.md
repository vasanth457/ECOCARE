# ECO CARE

ECO CARE is a Streamlit plant-care application.

## Run locally

1. Use Python 3.10 or newer.
2. Install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Add your Firebase service-account JSON file as `serviceAccountKey.json` in
   the project root. This file is ignored by Git and must never be published.
   The app checks the path in `GOOGLE_APPLICATION_CREDENTIALS` first, then
   Streamlit's `[firebase]` secret, and finally this local file. Remove or
   replace any stale key if Firebase reports `invalid_grant` or an invalid JWT
   signature.
4. Create a `.env` file for the API keys used by the app:

   ```dotenv
   FIREBASE_WEB_API_KEY=your_firebase_web_api_key
   GEMINI_API_KEY=your_gemini_api_key
   ACCUWEATHER_API_KEY=your_accuweather_api_key
   OPENWEATHERMAP_API_KEY=your_openweathermap_api_key
   ```

5. Start the app:

   ```powershell
   streamlit run app.py
   ```

Firebase Web, Gemini, and weather API keys should be set to enable their
respective services. Keep `.env`, `serviceAccountKey.json`, and
`.streamlit/secrets.toml` private.
Use a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
for `GEMINI_API_KEY`; do not use an OAuth access token. For a deployed app, set
the key in Streamlit Cloud secrets and reboot after changing it.

## Publish with Streamlit Community Cloud

1. Push this project to a GitHub repository. Do not upload `.env`,
   `serviceAccountKey.json`, or any other credential file.
2. In Streamlit Community Cloud, create an app from that repository and select
   `app.py` as the entry point.
3. In the app's **Settings > Secrets**, add the following TOML, replacing every
   placeholder with values from your Firebase service-account JSON and API
   providers:

   ```toml
   FIREBASE_WEB_API_KEY = "your_firebase_web_api_key"
   GEMINI_API_KEY = "your_gemini_api_key"
   ACCUWEATHER_API_KEY = "your_accuweather_api_key"
   OPENWEATHERMAP_API_KEY = "your_openweathermap_api_key"

   [firebase]
   type = "service_account"
   project_id = "your-firebase-project-id"
   private_key_id = "your-private-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\nPASTE_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n"
   client_email = "your-service-account@your-firebase-project-id.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "your-service-account-certificate-url"
   ```

   The service-account values are available from the current Firebase
   service-account JSON. If Firebase reports `invalid_grant` or an invalid JWT
   signature, generate a new private key for that service account, replace the
   entire `[firebase]` section with values from the new JSON, and reboot the
   app. Preserve the `\n` escapes in `private_key`. Remove any API-key entries
   for services you do not use.
4. Save the secrets and deploy. Streamlit installs the packages listed in
   `requirements.txt`.

Never commit real secrets, even temporarily. If a credential is exposed, revoke
or rotate it with its provider.
