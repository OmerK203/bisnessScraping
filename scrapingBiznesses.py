import requests
import time
import csv

API_KEY = ''  # Replace this
GEOCODE_URL = 'https://maps.googleapis.com/maps/api/geocode/json'
PLACES_NEARBY_URL = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
PLACE_DETAILS_URL = 'https://maps.googleapis.com/maps/api/place/details/json'

def get_zip_bounds(zip_code):
    params = {'address': zip_code, 'key': API_KEY}
    response = requests.get(GEOCODE_URL, params=params).json()
    results = response.get('results', [])
    if not results:
        return None

    geometry = results[0]['geometry']
    bounds = geometry.get('bounds') or geometry.get('viewport')
    if not bounds:
        return None

    ne = bounds['northeast']
    sw = bounds['southwest']
    return sw['lat'], ne['lat'], sw['lng'], ne['lng']

def generate_grid(sw_lat, ne_lat, sw_lng, ne_lng, step=0.02):
    lat_points = []
    lng_points = []
    lat = sw_lat
    while lat <= ne_lat:
        lat_points.append(lat)
        lat += step

    lng = sw_lng
    while lng <= ne_lng:
        lng_points.append(lng)
        lng += step

    return [(lat, lng) for lat in lat_points for lng in lng_points]

def get_places_near_point(lat, lng, radius_meters=2000):
    all_places = []
    next_page_token = None

    while True:
        params = {
            'key': API_KEY,
            'location': f"{lat},{lng}",
            'radius': radius_meters
        }
        if next_page_token:
            params['pagetoken'] = next_page_token
            time.sleep(2)

        response = requests.get(PLACES_NEARBY_URL, params=params).json()
        results = response.get('results', [])
        all_places.extend(results)

        next_page_token = response.get('next_page_token')
        if not next_page_token:
            break

    return all_places

def filter_places_without_website(places, zip_code):
    no_website_places = []
    seen = set()

    for idx, place in enumerate(places, start=1):
        place_id = place.get('place_id')
        if not place_id or place_id in seen:
            continue
        seen.add(place_id)

        details_params = {
            'key': API_KEY,
            'place_id': place_id,
            'fields': 'name,website,formatted_address,international_phone_number,url'
        }
        response = requests.get(PLACE_DETAILS_URL, params=details_params).json()
        result = response.get('result', {})
        if 'website' not in result:
            no_website_places.append({
                'ZIP Code': zip_code,
                'Name': result.get('name', 'N/A'),
                'Address': result.get('formatted_address', 'N/A'),
                'Phone Number': result.get('international_phone_number', 'N/A'),
                'Google Business Page': result.get('url', 'N/A')
            })

        time.sleep(0.1)

    return no_website_places

def write_to_csv(data, filename="businesses_without_website_multi_zip.csv"):
    fieldnames = ['ZIP Code', 'Name', 'Address', 'Phone Number', 'Google Business Page']

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

    print(f"\n✅ Data written to {filename}")

def process_zip_code(zip_code):
    bounds = get_zip_bounds(zip_code)
    if not bounds:
        print(f"❌ Could not get bounds for ZIP {zip_code}")
        return []

    sw_lat, ne_lat, sw_lng, ne_lng = bounds
    grid_points = generate_grid(sw_lat, ne_lat, sw_lng, ne_lng, step=0.02)

    print(f"🧭 Scanning {len(grid_points)} grid points inside ZIP code {zip_code}...\n")

    all_places = []
    for i, (lat, lng) in enumerate(grid_points):
        print(f"🔍 ZIP {zip_code} - Point {i + 1}/{len(grid_points)}: ({lat}, {lng})")
        places = get_places_near_point(lat, lng)
        all_places.extend(places)

    print(f"\n🧹 Filtering businesses without websites for ZIP {zip_code}...")
    return filter_places_without_website(all_places, zip_code)

def main():
    # Get 5 ZIP codes from user
    zip_codes = []
    for i in range(5):
        zip_code = input(f"Enter ZIP code #{i+1} (or press Enter to finish): ")
        if not zip_code:
            break
        zip_codes.append(zip_code)

    if not zip_codes:
        print("❌ No ZIP codes provided.")
        return

    print(f"\nProcessing {len(zip_codes)} ZIP codes: {', '.join(zip_codes)}")

    # Process all ZIP codes
    all_no_website_places = []
    for zip_code in zip_codes:
        places = process_zip_code(zip_code)
        all_no_website_places.extend(places)

    # Print results
    print(f"\n✅ Found {len(all_no_website_places)} businesses without websites across all ZIP codes:\n")

    # Write all data to single CSV
    write_to_csv(all_no_website_places)

if __name__ == '__main__':
    main()