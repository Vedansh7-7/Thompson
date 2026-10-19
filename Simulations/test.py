import configparser

config = configparser.ConfigParser()
config.read("config.ini")

scenario = "scenario_" + str(config["experiment"]["scenario"])
rates = config.get(scenario, "rates")
profits = config.get(scenario, "profits")

print("Rates:", rates)
print("Profits:", profits)