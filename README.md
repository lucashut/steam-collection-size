# Visualize the Size of a Steam Workshop Collection

Originally made for optimizing large collections of addons for Garry's Mod, this project uses Python and web scraping to find the total size of the collection. Since the project doesn't make use of APIs, it will break if Steam's HTML structure changes.

## Requirements

* Python
* URL for a public or unlisted collection
* Internet connection

## Usage

```
python main.py <collection_url>
```

## Note
To avoid compromising other downloads, the size of an item that fails to download will be set to zero, which will affect the total size.