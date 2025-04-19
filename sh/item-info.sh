#!/bin/bash

# Define the function to convert size to human-readable format
get_size_unit() {
     local size=$1
     local unit=("bytes" "KB" "MB" "GB")
     local index=0

     while ((size >= 1024)) && ((index < ${#unit[@]}-1)); do
          size=$(awk "BEGIN {printf \"%.2f\", $size / 1024}")
          ((index++))
     done

     echo "$size ${unit[index]}"
}

# Usage example:
size_in_bytes=1024
human_readable_size=$(get_size_unit $size_in_bytes)
echo "Human-readable size: $human_readable_size"

# Define the workshop item ID
workshopItemId=""

# Define the URL
url="https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"

# Make the POST request
response=$(curl -X POST "$url" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "itemcount=1" \
     -d "publishedfileids[0]=$workshopItemId")

title=$(echo "$response" | jq -r '.response.publishedfiledetails[0].title')
size=$(echo "$response" | jq -r '.response.publishedfiledetails[0].file_size')

echo "Title: $title"