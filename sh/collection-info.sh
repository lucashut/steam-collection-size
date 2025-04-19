#!/bin/bash

# Define the workshop item ID
workshopItemId=""

# Define the URL
url="https://api.steampowered.com/ISteamRemoteStorage/GetCollectionDetails/v1/"

# Make the POST request
curl -X POST "$url" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "collectioncount=1" \
     -d "publishedfileids[0]=$workshopItemId"
