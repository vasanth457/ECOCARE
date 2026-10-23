import os
import json
import html
import re
from datetime import datetime, timedelta
import streamlit as st
import requests

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

try:
    from static.weather.illustration_b64 import ILLUSTRATION_BASE64
except Exception:
    ILLUSTRATION_BASE64 = ""

# API Keys
USER_ACCUWEATHER_KEY = "zpka_b3f1db5ab12f4bb4ae8279ee65b6a169_a69e5944"
ACCU_LOCATION_CACHE = {}

STATES_DISTRICTS = {
    "Andhra Pradesh": ["Alluri Sitharama Raju","Anakapalli","Anantapur","Annamayya","Bapatla","Chittoor","East Godavari","Eluru","Guntur","Kadapa","Kakinada","Konaseema","Krishna","Kurnool","Nandyal","Nellore","NTR","Palnadu","Parvathipuram Manyam","Prakasam","Srikakulam","Sri Sathya Sai","Tirupati","Visakhapatnam","Vizianagaram","West Godavari"],
    "Arunachal Pradesh": ["Tawang","West Kameng","East Kameng","Papum Pare","Kurung Kumey","Kra Daadi","Lower Subansiri","Upper Subansiri","West Siang","East Siang","Siang","Upper Siang","Lower Siang","Lower Dibang Valley","Dibang Valley","Anjaw","Lohit","Namsai","Changlang","Tirap","Longding","Itanagar","Pakke Kessang","Kamle","Lepa Rada","Shi Yomi"],
    "Assam": ["Baksa","Barpeta","Biswanath","Bongaigaon","Cachar","Charaideo","Chirang","Darrang","Dhemaji","Dhubri","Dibrugarh","Goalpara","Golaghat","Hailakandi","Hojai","Jorhat","Kamrup","Kamrup Metro","Karbi Anglong","Karimganj","Kokrajhar","Lakhimpur","Majuli","Morigaon","Nagaon","Nalbari","Dima Hasao","Sivasagar","Sonitpur","South Salmara-Mankachar","Tinsukia","Udalguri","West Karbi Anglong"],
    "Bihar": ["Araria","Arwal","Aurangabad","Banka","Begusarai","Bhagalpur","Bhojpur","Buxar","Darbhanga","East Champaran","Gaya","Gopalganj","Jamui","Jehanabad","Kaimur","Katihar","Khagaria","Kishanganj","Lakhisarai","Madhepura","Madhubani","Munger","Muzaffarpur","Nalanda","Nawada","Patna","Purnia","Rohtas","Saharsa","Samastipur","Saran","Sheikhpura","Sheohar","Sitamarhi","Siwan","Supaul","Vaishali","West Champaran"],
    "Chhattisgarh": ["Balod","Baloda Bazar","Balrampur","Bastar","Bemetara","Bijapur","Bilaspur","Dantewada","Dhamtari","Durg","Gariaband","Gaurela-Pendra-Marwahi","Janjgir-Champa","Jashpur","Kabirdham","Kanker","Kondagaon","Korba","Koriya","Mahasamund","Mungeli","Narayanpur","Raigarh","Raipur","Rajnandgaon","Sukma","Surajpur","Surguja"],
    "Goa": ["North Goa","South Goa"],
    "Gujarat": ["Ahmedabad","Amreli","Anand","Aravalli","Banaskantha","Bharuch","Bhavnagar","Botad","Chhota Udepur","Dahod","Dang","Devbhoomi Dwarka","Gandhinagar","Gir Somnath","Jamnagar","Junagadh","Kheda","Kutch","Mahisagar","Mehsana","Morbi","Narmada","Navsari","Panchmahal","Patan","Porbandar","Rajkot","Sabarkantha","Surat","Surendranagar","Tapi","Vadodara","Valsad"],
    "Haryana": ["Ambala","Bhiwani","Charkhi Dadri","Faridabad","Fatehabad","Gurugram","Hisar","Jhajjar","Jind","Kaithal","Karnal","Kurukshetra","Mahendragarh","Nuh","Palwal","Panchkula","Panipat","Rewari","Rohtak","Sirsa","Sonipat","Yamunanagar"],
    "Himachal Pradesh": ["Bilaspur","Chamba","Hamirpur","Kangra","Kinnaur","Kullu","Lahaul and Spiti","Mandi","Shimla","Sirmaur","Solan","Una"],
    "Jharkhand": ["Bokaro","Chatra","Deoghar","Dhanbad","Dumka","East Singhbhum","Garhwa","Giridih","Godda","Gumla","Hazaribagh","Jamtara","Khunti","Koderma","Latehar","Lohardaga","Pakur","Palamu","Ramgarh","Ranchi","Sahibganj","Seraikela-Kharsawan","Simdega","West Singhbhum"],
    "Karnataka": ["Bagalkot","Ballari","Belagavi","Bengaluru Rural","Bengaluru Urban","Bidar","Chamarajanagar","Chikkaballapur","Chikkamagaluru","Chitradurga","Dakshina Kannada","Davangere","Dharwad","Gadag","Hassan","Haveri","Kalaburagi","Kodagu","Kolar","Koppal","Mandya","Mysuru","Raichur","Ramanagara","Shivamogga","Tumakuru","Udupi","Uttara Kannada","Vijayapura","Yadgir","Vijayanagara"],
    "Kerala": ["Alappuzha","Ernakulam","Idukki","Kannur","Kasaragod","Kollam","Kottayam","Kozhikode","Malappuram","Palakkad","Pathanamthitta","Thiruvananthapuram","Thrissur","Wayanad"],
    "Madhya Pradesh": ["Agar Malwa","Alirajpur","Anuppur","Ashoknagar","Balaghat","Barwani","Betul","Bhind","Bhopal","Burhanpur","Chhatarpur","Chhindwara","Damoh","Datia","Dewas","Dhar","Dindori","Guna","Gwalior","Harda","Hoshangabad","Indore","Jabalpur","Jhabua","Katni","Khandwa","Khargone","Mandla","Mandsaur","Morena","Narsinghpur","Neemuch","Panna","Raisen","Rajgarh","Ratlam","Rewa","Sagar","Satna","Sehore","Seoni","Shahdol","Shajapur","Sheopur","Shivpuri","Sidhi","Singrauli","Tikamgarh","Ujjain","Umaria","Vidisha"],
    "Maharashtra": ["Ahmednagar","Akola","Amravati","Aurangabad","Beed","Bhandara","Buldhana","Chandrapur","Dhule","Gadchiroli","Gondia","Hingoli","Jalgaon","Jalna","Kolhapur","Latur","Mumbai City","Mumbai Suburban","Nagpur","Nanded","Nandurbar","Nashik","Osmanabad","Palghar","Parbhani","Pune","Raigad","Ratnagiri","Sangli","Satara","Sindhudurg","Solapur","Thane","Wardha","Washim","Yavatmal"],
    "Manipur": ["Bishnupur","Chandel","Churachandpur","Imphal East","Imphal West","Jiribam","Kakching","Kamjong","Kangpokpi","Noney","Pherzawl","Senapati","Tamenglong","Tengnoupal","Thoubal","Ukhrul"],
    "Meghalaya": ["East Garo Hills","East Jaintia Hills","East Khasi Hills","North Garo Hills","Ri Bhoi","South Garo Hills","South West Garo Hills","South West Khasi Hills","West Garo Hills","West Jaintia Hills","West Khasi Hills","Eastern West Khasi Hills"],
    "Mizoram": ["Aizawl","Champhai","Hnahthial","Khawzawl","Kolasib","Lawngtlai","Lunglei","Mamit","Saiha","Saitual","Serchhip"],
    "Nagaland": ["Dimapur","Kiphire","Kohima","Longleng","Mokokchung","Mon","Peren","Phek","Tuensang","Wokha","Zunheboto","Chumoukedima","Noklak","Shamator","Niuland","Tseminyu"],
    "Odisha": ["Angul","Balangir","Balasore","Bargarh","Bhadrak","Boudh","Cuttack","Deogarh","Dhenkanal","Gajapati","Ganjam","Jagatsinghpur","Jajpur","Jharsuguda","Kalahandi","Kandhamal","Kendrapara","Kendujhar","Khordha","Koraput","Malkangiri","Mayurbhanj","Nabarangpur","Nayagarh","Nuapada","Puri","Rayagada","Sambalpur","Subarnapur","Sundargarh"],
    "Punjab": ["Amritsar","Barnala","Bathinda","Faridkot","Fatehgarh Sahib","Fazilka","Ferozepur","Gurdaspur","Hoshiarpur","Jalandhar","Kapurthala","Ludhiana","Mansa","Moga","Muktsar","Pathankot","Patiala","Rupnagar","Sahibzada Ajit Singh Nagar","Sangrur","Shaheed Bhagat Singh Nagar","Tarn Taran"],
    "Rajasthan": ["Ajmer","Alwar","Banswara","Baran","Barmer","Bharatpur","Bhilwara","Bikaner","Bundi","Chittorgarh","Churu","Dausa","Dholpur","Dungarpur","Hanumangarh","Jaipur","Jaisalmer","Jalore","Jhalawar","Jhunjhunu","Jodhpur","Karauli","Kota","Nagaur","Pali","Pratapgarh","Rajsamand","Sawai Madhopur","Sikar","Sirohi","Sri Ganganagar","Tonk","Udaipur","Kotputli-Behror","Khairthal-Tijara","Anupgarh","Balotra","Beawar","Didwana-Kuchaman","Deeg","Salumbar"],
    "Sikkim": ["East Sikkim","North Sikkim","South Sikkim","West Sikkim","Pakyong","Soreng"],
    "Tamil Nadu": ["Ariyalur","Chengalpattu","Chennai","Coimbatore","Cuddalore","Dharmapuri","Dindigul","Erode","Kallakurichi","Kanchipuram","Kanyakumari","Karur","Krishnagiri","Madurai","Mayiladuthurai","Nagapattinam","Namakkal","Nilgiris","Perambalur","Pudukkottai","Ramanathapuram","Ranipet","Salem","Sivaganga","Tenkasi","Thanjavur","Theni","Thoothukudi","Tiruchirappalli","Tirunelveli","Tirupathur","Tiruppur","Tiruvallur","Tiruvannamalai","Tiruvarur","Vellore","Viluppuram","Virudhunagar","Sirkazhi","Chidambaram","Kumbakonam"],
    "Telangana": ["Adilabad","Bhadradri Kothagudem","Hyderabad","Jagtial","Jangaon","Jayashankar Bhupalpally","Jogulamba Gadwal","Kamareddy","Karimnagar","Khammam","Komaram Bheem","Mahabubabad","Mahabubnagar","Mancherial","Medak","Medchal-Malkajgiri","Mulugu","Nagarkurnool","Nalgonda","Narayanpet","Nirmal","Nizamabad","Peddapalli","Rajanna Sircilla","Rangareddy","Sangareddy","Siddipet","Suryapet","Vikarabad","Wanaparthy","Warangal","Yadri Bhuvanagiri","Warangal Rural","Hanumakonda"],
    "Tripura": ["Dhalai","Gomati","Khowai","North Tripura","Sepahijala","South Tripura","Unakoti","West Tripura"],
    "Uttar Pradesh": ["Agra","Aligarh","Ambedkar Nagar","Amethi","Amroha","Auraiya","Ayodhya","Azamgarh","Baghpat","Bahraich","Ballia","Balrampur","Banda","Barabanki","Bareilly","Basti","Bhadohi","Bijnor","Budaun","Bulandshahr","Chandauli","Chitrakoot","Deoria","Etah","Etawah","Farrukhabad","Fatehpur","Firozabad","Gautam Buddha Nagar","Ghaziabad","Ghazipur","Gonda","Gorakhpur","Hamirpur","Hapur","Hardoi","Hathras","Jalaun","Jaunpur","Jhansi","Kannauj","Kanpur Dehat","Kanpur Nagar","Kasganj","Kaushambi","Kushinagar","Lakhimpur Kheri","Lalitpur","Lucknow","Maharajganj","Mahoba","Mainpuri","Mathura","Mau","Meerut","Mirzapur","Moradabad","Muzaffarnagar","Pilibhit","Pratapgarh","Prayagraj","Rae Bareli","Rampur","Saharanpur","Sambhal","Sant Kabir Nagar","Shahjahanpur","Shamli","Shrawasti","Siddharthnagar","Sitapur","Sonbhadra","Sultanpur","Unnao","Varanasi"],
    "Uttarakhand": ["Almora","Bageshwar","Chamoli","Champawat","Dehradun","Haridwar","Nainital","Pauri Garhwal","Pithoragarh","Rudraprayag","Tehri Garhwal","Udham Singh Nagar","Uttarkashi"],
    "West Bengal": ["Alipurduar","Bankura","Birbhum","Cooch Behar","Dakshin Dinajpur","Darjeeling","Hooghly","Howrah","Jalpaiguri","Jhargram","Kalimpong","Kolkata","Malda","Murshidabad","Nadia","North 24 Parganas","Paschim Bardhaman","Paschim Medinipur","Purba Bardhaman","Purba Medinipur","Purulia","South 24 Parganas","Uttar Dinajpur"],
    "Delhi": ["Central Delhi","East Delhi","New Delhi","North Delhi","North East Delhi","North West Delhi","Shahdara","South Delhi","South East Delhi","South West Delhi","West Delhi"],
    "Jammu and Kashmir": ["Anantnag","Bandipora","Baramulla","Budgam","Doda","Ganderbal","Jammu","Kathua","Kishtwar","Kulgam","Kupwara","Poonch","Pulwama","Rajouri","Ramban","Reasi","Samba","Shopian","Srinagar","Udhampur"],
    "Ladakh": ["Kargil","Leh"],
    "Puducherry": ["Puducherry","Karaikal","Mahe","Yanam"],
    "Chandigarh": ["Chandigarh"],
    "Andaman and Nicobar": ["North and Middle Andaman","South Andaman","Nicobar"],
    "Dadra and Nagar Haveli and Daman and Diu": ["Dadra and Nagar Haveli","Daman","Diu"],
    "Lakshadweep": ["Lakshadweep"]
}

ALL_STATES = list(STATES_DISTRICTS.keys())

def clean_html(raw_html: str) -> str:
    """
    Strips HTML comments and removes all leading/trailing whitespace from each line.
    Joining into zero-indentation HTML prevents Streamlit/Markdown parsers from ever
    mistaking HTML blocks for code blocks.
    """
    no_comments = re.sub(r'<!--.*?-->', '', raw_html, flags=re.DOTALL)
    lines = [line.strip() for line in no_comments.splitlines() if line.strip()]
    return "".join(lines)

def get_weather_svg(icon_key: str, size: int = 34) -> str:
    """Weather SVG Icons matching Google Weather dark theme aesthetic."""
    key = str(icon_key).lower()
    
    if "thunder" in key:
        return f'<svg width="{size}" height="{size}" viewBox="0 0 64 56" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M46 30H18C13 30 9 26 9 21.5C9 17.5 11.8 14.2 15.6 13.6C17 8 22 4 28 4C35 4 40.5 9 41.5 15.5C45.2 16.2 48 19.5 48 23.5C48 27.1 45.8 30 46 30Z" fill="url(#strmG)"/><path d="M28 26L21 38H28L25 48L37 34H29L34 26H28Z" fill="#FDD835" stroke="#FBC02D" stroke-width="0.8"/><circle cx="17" cy="42" r="2.2" fill="#64B5F6"/><circle cx="13" cy="49" r="2.2" fill="#64B5F6"/><circle cx="43" cy="40" r="2.2" fill="#64B5F6"/><circle cx="39" cy="48" r="2.2" fill="#64B5F6"/><defs><linearGradient id="strmG" x1="16" y1="4" x2="46" y2="30" gradientUnits="userSpaceOnUse"><stop stop-color="#546E7A"/><stop offset="1" stop-color="#37474F"/></linearGradient></defs></svg>'
    
    elif "rain" in key or "drizzle" in key or "shower" in key:
        return f'<svg width="{size}" height="{size}" viewBox="0 0 64 54" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M48 28H18C13.5 28 10 24.5 10 20C10 16 12.8 12.8 16.5 12C17.8 6.5 22.8 2.5 29 2.5C36 2.5 41.8 7.5 42.8 14C46.5 14.8 49.5 18 49.5 22C49.5 25.3 47 28 48 28Z" fill="url(#rnG)"/><line x1="20" y1="34" x2="16" y2="46" stroke="#42A5F5" stroke-width="3" stroke-linecap="round"/><line x1="31" y1="34" x2="27" y2="46" stroke="#42A5F5" stroke-width="3" stroke-linecap="round"/><line x1="42" y1="34" x2="38" y2="46" stroke="#42A5F5" stroke-width="3" stroke-linecap="round"/><defs><linearGradient id="rnG" x1="16" y1="2" x2="46" y2="28" gradientUnits="userSpaceOnUse"><stop stop-color="#78909C"/><stop offset="1" stop-color="#455A64"/></linearGradient></defs></svg>'
        
    elif "partly" in key or ("sun" in key and "cloud" in key):
        return f'<svg width="{size}" height="{size}" viewBox="0 0 64 50" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="44" cy="18" r="13" fill="url(#sunG)"/><path d="M42 40H16C11 40 7 36 7 31C7 26.8 10 23.2 14.2 22.5C15.6 16.2 21.2 11.5 27.8 11.5C35 11.5 41 16.8 41.8 24C45.5 24.6 48.5 28 48.5 32C48.5 36.4 45.2 40 42 40Z" fill="url(#cldG1)"/><defs><linearGradient id="sunG" x1="33" y1="8" x2="55" y2="28" gradientUnits="userSpaceOnUse"><stop stop-color="#FFD54F"/><stop offset="1" stop-color="#FFA000"/></linearGradient><linearGradient id="cldG1" x1="14" y1="11" x2="44" y2="40" gradientUnits="userSpaceOnUse"><stop stop-color="#FFFFFF"/><stop offset="1" stop-color="#B0BEC5"/></linearGradient></defs></svg>'
        
    elif "clear" in key or "sunny" in key:
        return f'<svg width="{size}" height="{size}" viewBox="0 0 54 54" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="27" cy="27" r="15" fill="url(#sunFull)"/><line x1="27" y1="4" x2="27" y2="8" stroke="#FFA000" stroke-width="3" stroke-linecap="round"/><line x1="27" y1="46" x2="27" y2="50" stroke="#FFA000" stroke-width="3" stroke-linecap="round"/><line x1="4" y1="27" x2="8" y2="27" stroke="#FFA000" stroke-width="3" stroke-linecap="round"/><line x1="46" y1="27" x2="50" y2="27" stroke="#FFA000" stroke-width="3" stroke-linecap="round"/><defs><linearGradient id="sunFull" x1="16" y1="16" x2="38" y2="38" gradientUnits="userSpaceOnUse"><stop stop-color="#FFEE58"/><stop offset="1" stop-color="#FF8F00"/></linearGradient></defs></svg>'
        
    elif "precip-icon" in key:
        return '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"/><path d="M8 19v2"/><path d="M8 13v2"/><path d="M16 19v2"/><path d="M16 13v2"/><path d="M12 21v2"/><path d="M12 15v2"/></svg>'
        
    elif "wind-icon" in key:
        return '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/></svg>'
        
    elif "humidity-icon" in key:
        return '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>'
        
    elif "aqi-icon" in key:
        return '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8c2.5-3 5.5-3 8 0s5.5 3 8 0 5.5-3 8 0"/><path d="M2 14c2.5-3 5.5-3 8 0s5.5 3 8 0 5.5-3 8 0"/><path d="M2 20c2.5-3 5.5-3 8 0s5.5 3 8 0 5.5-3 8 0"/></svg>'
        
    elif "chevron-down" in key:
        return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9AA0A6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
        
    # Default 3D Cumulus Cloud
    return f'<svg width="{size}" height="{size}" viewBox="0 0 64 48" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M48 38H18C12.5 38 8 33.5 8 28C8 23.2 11.4 19.2 16 18.2C17.5 11.2 23.6 6 31 6C39.5 6 46.5 12.5 47.3 20.8C51.6 21.6 55 25.4 55 30C55 34.4 51.9 38 48 38Z" fill="url(#cldMain)"/><defs><linearGradient id="cldMain" x1="16" y1="6" x2="48" y2="38" gradientUnits="userSpaceOnUse"><stop stop-color="#ECEFF1"/><stop offset="1" stop-color="#90A4AE"/></linearGradient></defs></svg>'

def render_weather_icon(icon_val, size=34) -> str:
    if not icon_val:
        return get_weather_svg("cloud", size=size)
    if isinstance(icon_val, str) and (icon_val.startswith("http://") or icon_val.startswith("https://") or icon_val.startswith("//")):
        url = f"https:{icon_val}" if icon_val.startswith("//") else icon_val
        return f'<img src="{url}" width="{size}" height="{size}" style="display:inline-block; vertical-align:middle; object-fit:contain;" alt="weather icon" />'
    return get_weather_svg(str(icon_val), size=size)

def map_accuweather_icon(icon_num: int, phrase: str = "") -> str:
    p = phrase.lower()
    if "thunder" in p:
        return "thunderstorm"
    if "rain" in p or "shower" in p or "drizzle" in p:
        return "rain"
    if icon_num in [15, 16, 17, 41, 42]:
        return "thunderstorm"
    elif icon_num in [12, 13, 14, 18, 26, 29, 39, 40]:
        return "rain"
    elif icon_num in [3, 4, 35, 36]:
        return "partly-cloudy"
    elif icon_num in [1, 2, 33, 34]:
        return "clear"
    else:
        return "cloud"

def get_demo_weather_sirkazhi(city: str = "Sirkazhi", state: str = "Tamil Nadu") -> dict:
    return {
        "city": city.title(),
        "state": state,
        "temp_c": 28,
        "condition_text": "Cloudy",
        "feelslike_c": 31,
        "hourly": [
            {"time": "Now", "temp": 28, "icon": "cloud", "rain_chance": 0},
            {"time": "9 am", "temp": 29, "icon": "cloud", "rain_chance": 0},
            {"time": "10 am", "temp": 31, "icon": "cloud", "rain_chance": 0},
            {"time": "11 am", "temp": 32, "icon": "rain", "rain_chance": 20},
            {"time": "12 pm", "temp": 32, "icon": "partly-cloudy", "rain_chance": 0},
            {"time": "1 pm", "temp": 33, "icon": "partly-cloudy", "rain_chance": 0}
        ],
        "daily": [
            {"day": "Tue", "max_temp": 33, "min_temp": 25, "icon": "thunderstorm", "condition": "Thunderstorm", "rain_chance": 65, "active": True},
            {"day": "Wed", "max_temp": 29, "min_temp": 24, "icon": "cloud", "condition": "Cloudy", "rain_chance": 20, "active": False},
            {"day": "Thu", "max_temp": 31, "min_temp": 24, "icon": "thunderstorm", "condition": "Thunderstorm", "rain_chance": 60, "active": False},
            {"day": "Fri", "max_temp": 29, "min_temp": 24, "icon": "thunderstorm", "condition": "Thunderstorm", "rain_chance": 55, "active": False},
            {"day": "Sat", "max_temp": 30, "min_temp": 23, "icon": "rain", "condition": "Rain", "rain_chance": 45, "active": False},
            {"day": "Sun", "max_temp": 29, "min_temp": 24, "icon": "partly-cloudy", "condition": "Partly Cloudy", "rain_chance": 20, "active": False},
            {"day": "Mon", "max_temp": 30, "min_temp": 24, "icon": "cloud", "condition": "Cloudy", "rain_chance": 15, "active": False}
        ],
        "details": {
            "precip": "10%",
            "precip_mm": 0.2,
            "wind": "6 kph",
            "wind_dir": "WNW",
            "humidity": "78%",
            "humidity_val": 78,
            "dew_point": "24°C",
            "aqi": 49,
            "aqi_status": "Good air quality",
            "pm25": "11.2 µg/m³",
            "pm10": "24.0 µg/m³"
        },
        "is_demo": True,
        "source": "Demo Benchmark (Sirkazhi)"
    }

@st.cache_data(ttl=300, show_spinner=False)
def get_weather_realtime(city: str, state: str = "Tamil Nadu") -> dict:
    """
    Fetches real-time weather using AccuWeather API with fallback to WeatherAPI / OpenWeatherMap
    and raises an explicit error when no live provider can serve the location.
    """
    accu_key = os.getenv("ACCUWEATHER_API_KEY", USER_ACCUWEATHER_KEY)
    
    # 1. Primary: AccuWeather.com (Live with User Key)
    if accu_key:
        try:
            # Check or fetch location key
            cache_key = (city.strip().casefold(), state.strip().casefold())
            loc_key = ACCU_LOCATION_CACHE.get(cache_key)
            found_city = city.title()
            
            if not loc_key:
                r_loc = requests.get(
                    f"http://dataservice.accuweather.com/locations/v1/cities/search?apikey={accu_key}&q={city}, {state}",
                    timeout=5
                )
                if r_loc.status_code == 200:
                    loc_json = r_loc.json()
                    if loc_json:
                        loc_key = loc_json[0]["Key"]
                        found_city = loc_json[0]["LocalizedName"]
                        ACCU_LOCATION_CACHE[cache_key] = loc_key
            
            if loc_key:
                # Current Conditions
                r_curr = requests.get(
                    f"http://dataservice.accuweather.com/currentconditions/v1/{loc_key}?apikey={accu_key}&details=true",
                    timeout=5
                )
                if r_curr.status_code == 200:
                    curr = r_curr.json()[0]
                    temp_c = round(curr["Temperature"]["Metric"]["Value"])
                    feelslike_c = round(curr.get("RealFeelTemperature", {}).get("Metric", {}).get("Value", temp_c))
                    cond_text = curr.get("WeatherText", "Unavailable")
                    humidity = curr.get("RelativeHumidity")
                    wind_speed = curr.get("Wind", {}).get("Speed", {}).get("Metric", {}).get("Value")
                    wind_kph = round(wind_speed) if wind_speed is not None else None
                    wind_dir = curr.get("Wind", {}).get("Direction", {}).get("Localized", "Unavailable")
                    precip_mm = curr.get("PrecipitationSummary", {}).get("Precipitation", {}).get("Metric", {}).get("Value")

                    # Hourly Forecast
                    r_h = requests.get(
                        f"http://dataservice.accuweather.com/forecasts/v1/hourly/12hour/{loc_key}?apikey={accu_key}&metric=true&details=true",
                        timeout=5
                    )
                    hourly_list = []
                    if r_h.status_code == 200:
                        for i, h in enumerate(r_h.json()[:6]):
                            dt = datetime.fromisoformat(h["DateTime"])
                            t_label = "Now" if i == 0 else dt.strftime("%I %p").lstrip("0").lower()
                            hourly_list.append({
                                "time": t_label,
                                "temp": round(h["Temperature"]["Value"]),
                                "icon": map_accuweather_icon(h.get("WeatherIcon", 7), h.get("IconPhrase", "")),
                                "rain_chance": round(h["PrecipitationProbability"]) if h.get("PrecipitationProbability") is not None else None
                            })

                    # Daily Forecast
                    r_d = requests.get(
                        f"http://dataservice.accuweather.com/forecasts/v1/daily/5day/{loc_key}?apikey={accu_key}&metric=true&details=true",
                        timeout=5
                    )
                    daily_list = []
                    if r_d.status_code == 200:
                        for i, d in enumerate(r_d.json().get("DailyForecasts", [])[:6]):
                            dt = datetime.fromisoformat(d["Date"])
                            day_label = dt.strftime("%a")
                            d_phrase = d.get("Day", {}).get("IconPhrase", "Cloudy")
                            d_icon_num = d.get("Day", {}).get("WeatherIcon", 7)
                            daily_list.append({
                                "day": day_label,
                                "max_temp": round(d["Temperature"]["Maximum"]["Value"]),
                                "min_temp": round(d["Temperature"]["Minimum"]["Value"]),
                                "icon": map_accuweather_icon(d_icon_num, d_phrase),
                                "condition": d_phrase,
                                "rain_chance": round(d["Day"]["PrecipitationProbability"]) if d.get("Day", {}).get("PrecipitationProbability") is not None else None,
                                "active": (i == 0)
                            })

                    return {
                        "city": found_city,
                        "state": state,
                        "temp_c": temp_c,
                        "condition_text": cond_text,
                        "feelslike_c": feelslike_c,
                        "hourly": hourly_list,
                        "daily": daily_list,
                        "details": {
                            "precip": f"{hourly_list[0]['rain_chance']}%" if hourly_list else "Unavailable",
                            "precip_mm": f"{precip_mm} mm" if precip_mm is not None else "Unavailable",
                            "wind": f"{wind_kph} kph" if wind_kph is not None else "Unavailable",
                            "wind_dir": wind_dir,
                            "humidity": f"{humidity}%" if humidity is not None else "Unavailable",
                            "humidity_val": humidity,
                            "dew_point": "Unavailable",
                            "aqi_status": "No live air-quality feed",
                        },
                        "is_demo": False,
                        "source": "AccuWeather Live Telemetry"
                    }
        except Exception:
            pass

    # 2. Fallback: OpenWeatherMap
    owm_key = os.getenv("OPENWEATHERMAP_API_KEY", "dc8a66f43df9b113c57067228e956a49")
    if owm_key:
        try:
            location_query = f"{city},{state},IN"
            w_url = f"https://api.openweathermap.org/data/2.5/weather?q={location_query}&units=metric&appid={owm_key}"
            f_url = f"https://api.openweathermap.org/data/2.5/forecast?q={location_query}&units=metric&appid={owm_key}"
            w_res = requests.get(w_url, timeout=5)
            f_res = requests.get(f_url, timeout=5)
            if w_res.status_code == 200 and f_res.status_code == 200:
                w_json = w_res.json()
                f_json = f_res.json()
                temp_c = round(w_json["main"]["temp"])
                feelslike_c = round(w_json["main"]["feels_like"])
                cond_text = w_json["weather"][0]["main"]
                humidity = w_json["main"]["humidity"]
                wind_kph = round(w_json["wind"]["speed"] * 3.6)
                
                hourly_list = []
                for i, item in enumerate(f_json.get("list", [])[:6]):
                    dt = datetime.fromtimestamp(item["dt"])
                    t_label = "Now" if i == 0 else dt.strftime("%I %p").lstrip("0").lower()
                    hourly_list.append({
                        "time": t_label,
                        "temp": round(item["main"]["temp"]),
                        "icon": item["weather"][0]["main"].lower(),
                        "rain_chance": round(item["pop"] * 100) if item.get("pop") is not None else None
                    })

                from collections import defaultdict
                day_groups = defaultdict(list)
                for item in f_json.get("list", []):
                    day_groups[item["dt_txt"].split(" ")[0]].append(item)
                
                daily_list = []
                for i, (d_str, items) in enumerate(list(day_groups.items())[:6]):
                    dt_obj = datetime.strptime(d_str, "%Y-%m-%d")
                    daily_list.append({
                        "day": dt_obj.strftime("%a"),
                        "max_temp": round(max(x["main"]["temp_max"] for x in items)),
                        "min_temp": round(min(x["main"]["temp_min"] for x in items)),
                        "icon": items[0]["weather"][0]["main"].lower(),
                        "condition": items[0]["weather"][0]["main"],
                        "rain_chance": round(max(x["pop"] for x in items if x.get("pop") is not None) * 100) if any(x.get("pop") is not None for x in items) else None,
                        "active": (i == 0)
                    })
                
                return {
                    "city": city.title(),
                    "state": state,
                    "temp_c": temp_c,
                    "condition_text": cond_text,
                    "feelslike_c": feelslike_c,
                    "hourly": hourly_list,
                    "daily": daily_list,
                    "details": {
                        "precip": "10%",
                        "precip_mm": 0.2,
                        "wind": f"{wind_kph} kph",
                        "wind_dir": "WNW",
                        "humidity": f"{humidity}%",
                        "humidity_val": humidity,
                        "dew_point": "Unavailable",
                        "aqi_status": "No live air-quality feed",
                    },
                    "is_demo": False,
                    "source": "OpenWeatherMap Live Telemetry"
                }
        except Exception:
            pass

    raise RuntimeError(
        f"Live weather is unavailable for {city}, {state}. Configure a valid "
        "weather provider API key or retry when the provider is reachable."
    )

def get_plant_watering_advice(temp: float, humidity: float, rain_chance: float, city: str) -> dict:
    if rain_chance > 70:
        action_text = f"🌧️ SKIP Watering - Heavy rain expected ({rain_chance}%)"
        water_amount = "Skip"
        soil_status = "Saturated / Rain"
        detail = "Natural precipitation will provide deep soil saturation. Suspend manual watering to avoid root rot and nutrient leaching."
    elif rain_chance > 40:
        action_text = f"⛅ LIGHT Watering - {rain_chance}% rain, water 0.5L only"
        water_amount = "0.5L"
        soil_status = "Moderate Moisture"
        detail = f"Moderate rain chance ({rain_chance}%). Provide a light topsoil moistening (0.5L) only for indoor or sheltered balcony pots."
    elif temp > 35 and humidity < 50:
        action_text = "🔥 HEAVY Watering - Hot & Dry, water 2.5L morning + evening"
        water_amount = "2.5L"
        soil_status = "High Demand"
        detail = "Intense heat combined with low humidity accelerates transpiration. Split 2.5L: 1.25L at sunrise (6:30 AM) and 1.25L at dusk (6:00 PM)."
    elif temp > 30:
        action_text = "☀️ NORMAL Watering - Water 1.5L in morning"
        water_amount = "1.5L"
        soil_status = "Normal Demand"
        detail = "Warm ambient temperatures. Apply 1.5L early morning before sunlight triggers high evaporation."
    else:
        action_text = "🌱 LIGHT Watering - Cool weather, 1L is enough"
        water_amount = "1L"
        soil_status = "Low Demand"
        detail = "Mild conditions reduce soil drying rate. 1.0L is sufficient to sustain healthy root zones."

    smart_tip = f"Best time to water in {city} today: 6:30 AM (Before heat)"
    return {
        "action_text": action_text,
        "water_amount": water_amount,
        "soil_status": soil_status,
        "detail": detail,
        "smart_tip": smart_tip
    }

def render_weather_html_card(data: dict) -> str:
    """
    Builds the pixel-perfect HTML card matching the dark theme screenshot.
    Uses clean_html to prevent any markdown code-block injection bugs.
    """
    city = data.get("city", "Unavailable")
    temp_c = data.get("temp_c", "Unavailable")
    condition_text = data.get("condition_text", "Unavailable")
    feelslike_c = data.get("feelslike_c", "Unavailable")
    hourly = data.get("hourly", [])
    daily = data.get("daily", [])
    details = data.get("details", {})
    
    # Bottom Landscape Illustration
    b64_img = ILLUSTRATION_BASE64
    if b64_img:
        illustration_html = f'<div style="margin: 18px -24px 0 -24px; width: calc(100% + 48px); border-radius: 0 0 24px 24px; overflow: hidden; line-height: 0;"><img src="data:image/png;base64,{b64_img}" style="width: 100%; height: auto; display: block; object-fit: cover;" alt="Weather Landscape" /></div>'
    else:
        illustration_html = '<div style="margin: 18px -24px 0 -24px; width: calc(100% + 48px); height: 95px; border-radius: 0 0 24px 24px; overflow: hidden; background: linear-gradient(180deg, #2A3831 0%, #1E4620 100%); display: flex; align-items: flex-end; justify-content: center;"><span style="font-size: 34px; margin-bottom: 8px;">🌳🌳🐸🌳🌳</span></div>'

    # Build Hourly Row without indentations
    hourly_items_html = ""
    for item in hourly[:6]:
        t_label = item.get("time", "")
        t_temp = item.get("temp", "—")
        t_icon = item.get("icon", "cloud")
        t_rain = item.get("rain_chance")
        
        rain_badge = f'<div style="color: #64B5F6; font-size: 11px; font-weight: 700; margin: 2px 0 3px 0; display: flex; align-items: center; justify-content: center; gap: 2px;">{t_rain}% <span style="font-size: 9px;">💧</span></div>' if t_rain is not None and t_rain > 0 else ('<div style="height: 16px;color:#9AA0A6;font-size:10px;">—</div>' if t_rain is None else '<div style="height: 16px;"></div>')
        icon_rendered = render_weather_icon(t_icon, size=32)
        
        hourly_items_html += f'<div style="display: flex; flex-direction: column; align-items: center; width: 16%;"><div style="color: #FFFFFF; font-size: 16px; font-weight: 600; line-height: 1.2;">{t_temp}°</div>{rain_badge}<div style="height: 32px; display: flex; align-items: center; justify-content: center;">{icon_rendered}</div><div style="color: #9AA0A6; font-size: 13px; font-weight: 400; margin-top: 8px;">{t_label}</div></div>'

    # Build 5-Day Horizontal Row
    daily_items_html = ""
    for i, d in enumerate(daily[:6]):
        day_name = d.get("day", "")
        max_t = d.get("max_temp", "—")
        min_t = d.get("min_temp", "—")
        d_icon = d.get("icon", "cloud")
        is_active = d.get("active", False) or (i == 0)
        
        border_style = "1.5px solid #FFFFFF" if is_active else "1px solid #383C42"
        bg_style = "#2D3035" if is_active else "#25272B"
        shadow_style = "box-shadow: 0 4px 16px rgba(0,0,0,0.35);" if is_active else ""
        icon_rendered = render_weather_icon(d_icon, size=34)
        
        daily_items_html += f'<div style="background: {bg_style}; border: {border_style}; border-radius: 18px; padding: 14px 6px; flex: 1; min-width: 72px; text-align: center; box-sizing: border-box; {shadow_style}"><div style="color: #FFFFFF; font-size: 14.5px; font-weight: 600; margin-bottom: 6px;">{day_name}</div><div style="height: 34px; display: flex; align-items: center; justify-content: center; margin: 4px 0;">{icon_rendered}</div><div style="color: #FFFFFF; font-size: 13px; font-weight: 500; margin-top: 6px;">{max_t}°/{min_t}°</div></div>'

    # Details values
    precip_val = details.get("precip", "Unavailable")
    precip_mm = details.get("precip_mm", "Unavailable")
    wind_val = details.get("wind", "Unavailable")
    wind_dir = details.get("wind_dir", "Unavailable")
    humidity_val = details.get("humidity", "Unavailable")
    dew_pt = details.get("dew_point", "Unavailable")
    aqi_num = details.get("aqi", "Unavailable")
    aqi_stat = details.get("aqi_status", "No live air-quality feed")
    aqi_color = "#34A853" if details.get("aqi") is not None else "#9AA0A6"
    pm25 = details.get("pm25", "Unavailable")
    pm10 = details.get("pm10", "Unavailable")
    big_cloud_svg = get_weather_svg("cloud", size=48)

    raw_html = f'''
    <style>
        .ecocare-weather-wrapper {{
            max-width: 540px;
            margin: 0 auto;
            font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            -webkit-font-smoothing: antialiased;
        }}
        .weather-now-card {{
            background: linear-gradient(180deg, #2E3330 0%, #25282B 55%, #1F2124 100%);
            border-radius: 24px;
            padding: 24px 24px 0 24px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
            position: relative;
            overflow: hidden;
            box-sizing: border-box;
        }}
        .weather-detail-row {{
            background: #25272B;
            border-radius: 16px;
            margin-bottom: 10px;
            border: 1px solid #34383E;
            overflow: hidden;
            transition: background 0.2s ease;
        }}
        .weather-detail-row summary {{
            list-style: none !important;
            outline: none !important;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 18px;
            cursor: pointer;
            user-select: none;
        }}
        .weather-detail-row summary::-webkit-details-marker {{
            display: none !important;
        }}
        .weather-detail-row[open] .detail-chevron {{
            transform: rotate(180deg);
        }}
        .detail-chevron {{
            transition: transform 0.2s ease;
            color: #9AA0A6;
            display: flex;
            align-items: center;
        }}
    </style>
    <div class="ecocare-weather-wrapper">
        <div class="weather-now-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="color: #9AA0A6; font-size: 15px; font-weight: 500; margin-bottom: 2px;">Now</div>
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <span style="font-size: 64px; font-weight: 700; color: #FFFFFF; line-height: 1; letter-spacing: -2px;">{temp_c}°</span>
                        <div style="margin-bottom: 2px;">{big_cloud_svg}</div>
                    </div>
                </div>
                <div style="text-align: right; padding-top: 8px;">
                    <div style="color: #FFFFFF; font-size: 20px; font-weight: 600; letter-spacing: -0.2px;">{condition_text}</div>
                    <div style="color: #9AA0A6; font-size: 14px; font-weight: 400; margin-top: 4px;">Feels like {feelslike_c}°</div>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: flex-end; margin: 26px 0 16px 0; text-align: center;">
                {hourly_items_html}
            </div>
            {illustration_html}
        </div>
        <div style="display: flex; gap: 8px; margin: 14px 0 16px 0; overflow-x: auto; padding-bottom: 4px; scrollbar-width: none;">
            {daily_items_html}
        </div>
        <div>
            <details class="weather-detail-row">
                <summary>
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <div style="width: 44px; height: 44px; background: #35383E; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            {get_weather_svg("precip-icon")}
                        </div>
                        <div style="color: #FFFFFF; font-size: 16px; font-weight: 500;">
                            Precipitation <span style="color: #8E9297; margin: 0 4px;">·</span> {precip_val}
                        </div>
                    </div>
                    <div class="detail-chevron">{get_weather_svg("chevron-down")}</div>
                </summary>
                <div style="padding: 4px 18px 16px 18px; color: #B0BEC5; font-size: 13.5px; border-top: 1px solid #34383E; margin-top: 2px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
                        <div><b>Expected Rain:</b> {precip_mm} mm</div>
                        <div><b>Probability:</b> {precip_val}</div>
                    </div>
                    <div style="margin-top: 8px; color: #81C784;">💡 <b>Soil Tip:</b> Monitor natural soil hydration against scheduled watering volume.</div>
                </div>
            </details>
            <details class="weather-detail-row">
                <summary>
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <div style="width: 44px; height: 44px; background: #35383E; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            {get_weather_svg("wind-icon")}
                        </div>
                        <div style="color: #FFFFFF; font-size: 16px; font-weight: 500;">
                            Wind <span style="color: #8E9297; margin: 0 4px;">·</span> {wind_val}
                        </div>
                    </div>
                    <div class="detail-chevron">{get_weather_svg("chevron-down")}</div>
                </summary>
                <div style="padding: 4px 18px 16px 18px; color: #B0BEC5; font-size: 13.5px; border-top: 1px solid #34383E; margin-top: 2px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
                        <div><b>Direction:</b> {wind_dir}</div>
                        <div><b>Velocity:</b> {wind_val}</div>
                    </div>
                    <div style="margin-top: 8px; color: #81C784;">💡 <b>Garden Tip:</b> Gentle breeze. Safe for delicate seedlings and terrace pots.</div>
                </div>
            </details>
            <details class="weather-detail-row">
                <summary>
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <div style="width: 44px; height: 44px; background: #35383E; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            {get_weather_svg("humidity-icon")}
                        </div>
                        <div style="color: #FFFFFF; font-size: 16px; font-weight: 500;">
                            Humidity <span style="color: #8E9297; margin: 0 4px;">·</span> {humidity_val}
                        </div>
                    </div>
                    <div class="detail-chevron">{get_weather_svg("chevron-down")}</div>
                </summary>
                <div style="padding: 4px 18px 16px 18px; color: #B0BEC5; font-size: 13.5px; border-top: 1px solid #34383E; margin-top: 2px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
                        <div><b>Relative Humidity:</b> {humidity_val}</div>
                        <div><b>Dew Point:</b> {dew_pt}</div>
                    </div>
                    <div style="margin-top: 8px; color: #81C784;">💡 <b>Transpiration Tip:</b> Atmospheric moisture helps retain root hydration.</div>
                </div>
            </details>
            <details class="weather-detail-row">
                <summary>
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <div style="width: 44px; height: 44px; background: #35383E; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            {get_weather_svg("aqi-icon")}
                        </div>
                        <div style="color: #FFFFFF; font-size: 16px; font-weight: 500;">
                            Air quality <span style="color: #8E9297; margin: 0 4px;">·</span> <span style="display:inline-block; width:9px; height:9px; border-radius:50%; background-color:{aqi_color}; margin-right:4px;"></span> {aqi_num} <span style="color: #8E9297; margin: 0 4px;">·</span> {aqi_stat}
                        </div>
                    </div>
                    <div class="detail-chevron">{get_weather_svg("chevron-down")}</div>
                </summary>
                <div style="padding: 4px 18px 16px 18px; color: #B0BEC5; font-size: 13.5px; border-top: 1px solid #34383E; margin-top: 2px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
                        <div><b>PM2.5:</b> {pm25}</div>
                        <div><b>PM10:</b> {pm10}</div>
                    </div>
                    <div style="margin-top: 8px; color: #81C784;">💡 <b>Air Health:</b> Clean air promotes healthy respiration and photosynthesis.</div>
                </div>
            </details>
        </div>
    </div>
    '''
    return clean_html(raw_html)

def render_plant_watering_card(data: dict) -> str:
    """
    Renders the EcoCare Green Card #E8F5E9 with dynamic watering logic & weekly schedule table.
    Uses clean_html to prevent markdown code block bugs.
    """
    city = data.get("city", "your location")
    temp_c = data.get("temp_c")
    humidity_val = data.get("details", {}).get("humidity_val")
    daily = data.get("daily", [])
    if not daily:
        return clean_html(
            '<div style="max-width:540px;margin:24px auto;padding:18px;border-radius:16px;'
            'background:#fff8e1;color:#5d4a1c;border:1px solid #f0dfaa;">'
            'A live forecast is not available, so weather-based watering advice is paused.'
            '</div>'
        )

    today_rain = daily[0].get("rain_chance")
    if temp_c is None or humidity_val is None or today_rain is None:
        return clean_html(
            '<div style="max-width:540px;margin:24px auto;padding:18px;border-radius:16px;'
            'background:#fff8e1;color:#5d4a1c;border:1px solid #f0dfaa;">'
            'Live forecast details are incomplete, so weather-based watering advice is paused.'
            '</div>'
        )
    today_advice = get_plant_watering_advice(temp_c, humidity_val, today_rain, city)

    weekly_rows_html = ""
    for i, d in enumerate(daily[:6]):
        d_day = d.get("day", "")
        d_cond = d.get("condition", "Unavailable")
        d_max = d.get("max_temp", "—")
        d_min = d.get("min_temp", "—")
        d_rain = d.get("rain_chance")
        
        cond_lower = d_cond.lower()
        if "thunder" in cond_lower:
            w_icon = "⛈️ Thunder"
        elif "rain" in cond_lower or "shower" in cond_lower:
            w_icon = "🌧️ Rain"
        elif "partly" in cond_lower or "sun" in cond_lower:
            w_icon = "⛅ Partly Cloudy"
        elif "clear" in cond_lower:
            w_icon = "☀️ Clear"
        else:
            w_icon = "☁️ Cloudy"

        if d_rain is None:
            water_tag = '<span style="background:#F3F4F4; color:#64716C; font-weight:700; padding:4px 10px; border-radius:12px; font-size:12px;">No rain data</span>'
            soil_text = "Unavailable"
        elif d_rain > 70:
            water_tag = '<span style="background:#FFEBEE; color:#C62828; font-weight:700; padding:4px 10px; border-radius:12px; font-size:12px;">🌧️ Skip</span>'
            soil_text = "Saturated / Rain"
        elif d_rain > 40:
            water_tag = '<span style="background:#E0F2F1; color:#00695C; font-weight:700; padding:4px 10px; border-radius:12px; font-size:12px;">⛅ 0.5L</span>'
            soil_text = "Light Damp"
        elif d_max > 35 and humidity_val < 50:
            water_tag = '<span style="background:#FFF3E0; color:#E65100; font-weight:700; padding:4px 10px; border-radius:12px; font-size:12px;">🔥 2.5L</span>'
            soil_text = "High Demand"
        elif d_max > 30:
            water_tag = '<span style="background:#E8F5E9; color:#1B5E20; font-weight:700; padding:4px 10px; border-radius:12px; font-size:12px;">☀️ 1.5L</span>'
            soil_text = "Standard"
        else:
            water_tag = '<span style="background:#E8F5E9; color:#1B5E20; font-weight:700; padding:4px 10px; border-radius:12px; font-size:12px;">🌱 1.0L</span>'
            soil_text = "Optimal"

        row_bg = "#F1F8F3" if i == 0 else "#FFFFFF"
        today_marker = '<span style="background:#1E5A3A; color:#FFF; font-size:10px; padding:2px 6px; border-radius:8px; margin-left:4px;">TODAY</span>' if i == 0 else ''
        
        weekly_rows_html += f'<tr style="background: {row_bg}; border-bottom: 1px solid #E0E8E2;"><td style="padding: 12px 14px; font-weight: 600; color: #1A1A1A;">{d_day} {today_marker}</td><td style="padding: 12px 14px; color: #2D3748;">{w_icon}</td><td style="padding: 12px 14px; font-weight: 500; color: #1A1A1A;">{d_max}°/{d_min}°</td><td style="padding: 12px 14px;">{water_tag}</td><td style="padding: 12px 14px; color: #5A6D5E; font-size: 13px;">{soil_text}</td></tr>'

    green_card_html = f'''
    <div style="max-width: 540px; margin: 24px auto 0 auto; background: #E8F5E9; border: 1.5px solid #C8E6C9; border-radius: 20px; padding: 22px; box-shadow: 0 4px 18px rgba(14,47,36,0.06); font-family: 'Poppins', sans-serif;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
            <span style="font-size: 24px;">🌿</span>
            <h3 style="margin: 0; font-size: 19px; font-weight: 700; color: #1E5A3A;">Plant Watering Schedule (Weather-Tuned)</h3>
        </div>
        <div style="color: #4A6351; font-size: 13.5px; margin-bottom: 16px;">
            Daily hydration prescriptions calibrated to {city}'s live atmospheric conditions.
        </div>
        <div style="background: #FFFFFF; border: 1px solid #C8E6C9; border-radius: 14px; padding: 16px; margin-bottom: 14px;">
            <div style="font-size: 12px; font-weight: 700; color: #5A6D5E; text-transform: uppercase; letter-spacing: 0.5px;">Today's Hydration Directive</div>
            <div style="font-size: 18px; font-weight: 700; color: #1E5A3A; margin: 6px 0;">{today_advice["action_text"]}</div>
            <div style="font-size: 13.5px; color: #4A5568; line-height: 1.45;">{today_advice["detail"]}</div>
        </div>
        <div style="background: #C8E6C9; border-left: 4px solid #1E5A3A; border-radius: 8px; padding: 12px 14px; margin-bottom: 18px; color: #0E2F24; font-size: 13.5px; font-weight: 600;">
            💡 {today_advice["smart_tip"]}
        </div>
        <div style="font-weight: 700; font-size: 14.5px; color: #1E5A3A; margin-bottom: 8px;">Weekly Irrigation Forecast:</div>
        <div style="overflow-x: auto; border-radius: 12px; border: 1px solid #C8E6C9;">
            <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                <thead>
                    <tr style="background: #1E5A3A; color: #FFFFFF;">
                        <th style="padding: 10px 14px;">Day</th>
                        <th style="padding: 10px 14px;">Weather</th>
                        <th style="padding: 10px 14px;">Temp</th>
                        <th style="padding: 10px 14px;">Water</th>
                        <th style="padding: 10px 14px;">Soil Demand</th>
                    </tr>
                </thead>
                <tbody>
                    {weekly_rows_html}
                </tbody>
            </table>
        </div>
    </div>
    '''
    return clean_html(green_card_html)

def weather_monitoring_page():
    """
    Main View Function for Real-Time Weather Monitoring System.
    """
    user_location = st.session_state.get("user", {}).get("location", "Sirkazhi, Tamil Nadu")
    
    default_state = "Tamil Nadu"
    default_district = "Sirkazhi"
    if "," in user_location:
        parts = [p.strip() for p in user_location.split(",")]
        if len(parts) >= 2:
            potential_state = parts[1]
            potential_district = parts[0]
            if potential_state in ALL_STATES:
                default_state = potential_state
                if potential_district in STATES_DISTRICTS.get(default_state, []):
                    default_district = potential_district

    if "selected_state" not in st.session_state:
        st.session_state["selected_state"] = default_state
    if "selected_district" not in st.session_state:
        st.session_state["selected_district"] = default_district

    # Header
    user_name = st.session_state.get("user", {}).get("name", "Plant lover")
    st.markdown(f"## 🌦️ **Weather Monitoring · {user_name}**")
    st.caption("Live weather telemetry and location-specific plant care.")

    # 1. Cascading State + District + Search Selectors
    st.markdown("##### 📍 Location Telemetry Controls")
    col_state, col_dist, col_search = st.columns([1.2, 1.2, 1.6])
    
    with col_state:
        state_idx = ALL_STATES.index(st.session_state["selected_state"]) if st.session_state["selected_state"] in ALL_STATES else 0
        current_state = st.selectbox(
            "Select State (28 States + 8 UTs):",
            options=ALL_STATES,
            index=state_idx,
            key="weather_state_selector"
        )
        if current_state != st.session_state["selected_state"]:
            st.session_state["selected_state"] = current_state
            dist_list = STATES_DISTRICTS.get(current_state, ["Chennai"])
            st.session_state["selected_district"] = "Sirkazhi" if current_state == "Tamil Nadu" else dist_list[0]
            st.session_state["custom_city_input"] = ""
            st.rerun()

    with col_dist:
        dist_options = STATES_DISTRICTS.get(st.session_state["selected_state"], ["Chennai"])
        dist_idx = dist_options.index(st.session_state["selected_district"]) if st.session_state["selected_district"] in dist_options else 0
        current_dist = st.selectbox(
            f"Select District ({st.session_state['selected_state']}):",
            options=dist_options,
            index=dist_idx,
            key="weather_dist_selector"
        )
        if current_dist != st.session_state["selected_district"]:
            st.session_state["selected_district"] = current_dist
            st.session_state["custom_city_input"] = ""
            if "user" in st.session_state:
                st.session_state["user"]["location"] = f"{current_dist}, {st.session_state['selected_state']}"
            st.rerun()

    with col_search:
        custom_city_input = st.text_input(
            "Type any village/city in India:",
            placeholder="e.g. Sirkazhi, Mayiladuthurai, Manali, Ooty...",
            key="custom_city_input"
        )

    # Action Toolbar
    act_col1, act_col2, act_col3 = st.columns([1.5, 1.5, 3])
    with act_col1:
        st.button("🔄 Live Update", use_container_width=True)
    with act_col2:
        auto_ref = st.checkbox("⏱️ Auto-refresh (5 mins)", value=False, key="weather_auto_ref_toggle")
        if auto_ref and AUTOREFRESH_AVAILABLE:
            st_autorefresh(interval=300000, key="weather_autorefresh_timer")
    with act_col3:
        effective_city = custom_city_input.strip() if custom_city_input.strip() else st.session_state["selected_district"]
        effective_state = st.session_state["selected_state"]
        active_location = f"{effective_city}, {effective_state}"
        if "user" in st.session_state:
            st.session_state["user"]["location"] = active_location
        st.markdown(
            f"""<div style="padding: 8px 12px; background: #E8F5E9; border-radius: 10px; color: #1E5A3A; font-weight: 600; font-size: 13px; text-align: right;">
                📍 Active: <b>{effective_city}, {effective_state}</b>
            </div>""",
            unsafe_allow_html=True
        )

    # 2. Fetch Weather Data with spinner
    try:
        with st.spinner(f"Fetching real-time atmospheric conditions for {effective_city}..."):
            weather_data = get_weather_realtime(effective_city, effective_state)
    except (RuntimeError, ValueError) as error:
        st.error(str(error))
        st.info("Weather data is not being replaced with sample or cached demo conditions.")
        from dashboard import render_compact_plant_library
        render_compact_plant_library()
        return

    source_tag = weather_data.get("source", "Telemetry Stream")
    badge_color = "#37474F"
    st.markdown(
        f"""<div style="text-align: center; margin-bottom: 12px;">
            <span style="background: {badge_color}; color: #FFFFFF; font-size: 11.5px; padding: 4px 12px; border-radius: 20px; font-weight: 500;">
                ⚡ {source_tag} &nbsp;|&nbsp; Updated: {datetime.now().strftime("%I:%M %p")}
            </span>
        </div>""",
        unsafe_allow_html=True
    )

    # 3. RENDER DARK WEATHER CARD (EXACT SCREENSHOT DESIGN)
    dark_card_html = render_weather_html_card(weather_data)
    st.markdown(dark_card_html, unsafe_allow_html=True)

    # 4. RENDER PLANT WATERING SCHEDULE (ECOCARE GREEN CARD #E8F5E9)
    watering_card_html = render_plant_watering_card(weather_data)
    st.markdown(watering_card_html, unsafe_allow_html=True)

    # Keep the full plant catalog available alongside weather-based care advice.
    from dashboard import render_compact_plant_library
    render_compact_plant_library()
