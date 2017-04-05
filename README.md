# hermes-server


## Why track Uber prices?

Because they vary a crazy lot. Example: In the summer Uber pool rates between
my office and apartment varied between $3 and $15, and this was without surge.
Hermes tracks Uber prices from a particular source to destination and stores them in an elastic search db for pretty kibana visuals.

<img src="http://i.imgur.com/LaHq9TC.png" style="height: 720px; width: 450px;"/>



## Use
* Contains a django API (unprotected for now) you can make calls to set start and end points to track prices for.
    * Offers an endpoint o get static graph of tracked prices between two tracked coordinates (pretty much all it does right now, see coming soon)
* Another script `uber_miner/main.py` actually tracks these points, updating prices every two minutes. (Sequentially for now)
* Also has an accompanying Android app that actually makes calls to said API, built by my team at LAHacks (needs more work though)
    * [Find it here](https://github.com/maniknarang/RIDERR)

## Coming soon
* Doesn't track uber pool prices, changing in next update. That requires OAuth tokens.
* Machine learning to predict the optimal travel times for lowest uber rates.
* Lots of other fixes/improvements.


## Warning
Storing Uber price data violates the API's terms of use, so, er, don't use it?
Should be fine for personal use, really.

An online learning model might not violate them however.
