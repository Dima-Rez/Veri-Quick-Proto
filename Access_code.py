import dropbox

# Replace with your app key, app secret, and the authorization code
APP_KEY = 'd61ut2ksugn18d2'
APP_SECRET = '4nnvx9xhdonh756'
AUTHORIZATION_CODE = 'KJm_TrFbXkgAAAAAAAAAWfcTjYbp837VZU0Ksdi9qWk'
REDIRECT_URI = 'https://edv-server.streamlit.app/'

# Initialize Dropbox OAuth2 flow
auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET)

# Fetch access token and refresh token
token_result = auth_flow.finish(AUTHORIZATION_CODE)
print("Access Token:", token_result.access_token)
print("Refresh Token:", token_result.refresh_token)
