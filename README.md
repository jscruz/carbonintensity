# carbonintensity

<!-- badges start -->

[![Maintained][Maintained]](#)
[![BuyMeCoffee][buymecoffeebadge]][buymecoffeelink]

<!-- badges end -->

_Simple Carbon Intensity UK API Library_

The purpose of this library is to retrieve information from [Carbon Intensity UK](https://carbonintensity.org.uk/)

The client connects asynchrnously to the API for retrieving information about the current level of CO2 generating energy in the current period.

It uses `aiohttp` to communicate with the API asynchrnously. This decision has been based mainly on the premise that the library will be used in the context of Home Assistant integration.

In addition it calculates when is the next 24 hours lowest level comparing values of the CO2 forecast levels.

## Example

Retrieve regional information based on postcode `SW1` for the next 24 hours starting now:

```python
   client = Client("SW1")
   response = await client.async_get_data()
   data = response["data"]
```
Note: Time in UTC

## Data format

An example of the function output can be found below:

```json
   {
       "data":
        {
              "current_period_from": "2020-05-20T10:00Z",
              "current_period_to": "2020-05-20T10:30Z",
              "current_period_forecast":300,
              "current_period_index": "high",
              "lowest_period_from":"2020-05-21T14:00Z",
              "lowest_period_to":"2020-05-21T14:30Z",
              "lowest_period_forecast": 168,
              "lowest_period_index": "moderate",
              "postcode": "SW1"
        }
    }
```

## Install carbonintensity

```bash
python3 -m pip install -U carbonintensity
```

<!-- links start -->

[buymecoffeelink]:https://www.buymeacoffee.com/jscruz
[buymecoffeebadge]: https://camo.githubusercontent.com/cd005dca0ef55d7725912ec03a936d3a7c8de5b5/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f6275792532306d6525323061253230636f666665652d646f6e6174652d79656c6c6f772e737667
[maintained]: https://img.shields.io/maintenance/yes/2020.svg

<!-- links end -->

## Licenses

This work is based on [sampleclient](https://github.com/ludeeus/sampleclient): See [Original license](./licenses/sampleclient/LICENSE)
