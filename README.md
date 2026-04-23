## campsite-checker

A Python script that checks recreation.gov for campsite availability and automatically books when a site opens up.

### Dependencies

* Python 3.8+
* pip

### Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright's Chromium browser
playwright install chromium
```

### Configuration

Copy `checker_example.yaml` to `checker.yaml` and edit all fields:

```bash
cp checker_example.yaml checker.yaml
```

You'll need:
- Your **recreation.gov login** credentials
- The **facility ID** of the campground (found in the URL: `recreation.gov/camping/campgrounds/<facility_id>`)
- Optionally, specific **campsite IDs** to target

### Usage

```bash
# Check once and attempt to book
python3 checker.py

# Poll every 60 seconds
python3 checker.py --poll 60

# Poll with a retry limit
python3 checker.py --poll 60 --max-retries 50

# Run with visible browser for debugging
python3 checker.py --headed

# Use a different config file
python3 checker.py --config my-config.yaml
```

### How it works

1. **Availability check** — queries recreation.gov's API to find available campsites for your requested dates. No browser needed for this step.
2. **Auto-book** — when a site is found, Playwright launches a browser, logs into your account, and walks through the reservation flow up to checkout.
3. **Payment** — you complete payment manually (the script does not store payment info).

### Finding facility and campsite IDs

Visit the campground page on recreation.gov. The facility ID is in the URL:

```
https://www.recreation.gov/camping/campgrounds/232447
                                                ^^^^^^ facility_id
```

To find specific campsite IDs, click on a campsite from the campground page. The campsite ID appears in the URL:

```
https://www.recreation.gov/camping/campsites/1234
                                              ^^^^ campsite_id
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0    | Booking reached checkout |
| 1    | No availability found / retries exhausted |
| 2    | Availability was found but every booking attempt failed |
