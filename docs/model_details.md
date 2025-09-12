1) Model Introduction 

Our forecasts use a Negative Binomial Generalized Linear Mixed Model (GLMM). We arrived at this choice after testing a range of alternatives in line with a Bayesian approach that acknowledges uncertainty about key modeling decisions. In particular, we considered four sources of uncertainty: (1) the definition of the training sample, (2) the probability distribution used to capture the count nature of conflict events, (3) the way in which temporal dynamics are modeled (e.g., autoregression, local and global trends, country effects), and (4) the criteria used to evaluate the resulting forecasts. Rather than assuming we knew the right answers in advance, we compared multiple plausible models across these dimensions. Through this process, we found that the Negative Binomial GLMM provided the strongest balance: it captures overdispersion in the data, incorporates dynamics across time and countries, and performed consistently well under forecast evaluation metrics.

Our forecasts are produced with a Negative Binomial Generalized Linear Mixed Model. 

We decided to use this model 

2) Defense of Model Choice
The starting point was a candidate set that combined three possible statistical distributions with two model frameworks. The distributions were:
Poisson, a common baseline for count data but one that assumes the mean and variance are equal.


Negative Binomial, which relaxes that assumption and allows for overdispersion (i.e., greater variance than the mean).


Tweedie, a more flexible alternative that can approximate compound Poisson processes and handle skewed counts.


These were each estimated within:
GAMs (Generalized Additive Models), which use smooth functions of time to capture nonlinear trends, and


GLMMs (Generalized Linear Mixed Models), which incorporate hierarchical structure, autoregressive terms, and country-specific effects.


This produced a candidate set of six models: Poisson GAM, Poisson GLMM, Negative Binomial GAM, Negative Binomial GLMM, Tweedie GAM, and Tweedie GLMM.
Why Negative Binomial?
 The comparisons showed that models with explicit overdispersion terms (Negative Binomial or Tweedie) consistently outperformed Poisson models. Poisson was too restrictive and produced poorer fit across all scoring rules. Between Negative Binomial and Tweedie, both performed well, but the Negative Binomial models tended to score slightly better on the main evaluation metrics (RMSE, CRPS, Brier). The Negative Binomial distribution is also standard for count data in conflict research, making it both reliable and interpretable.
Why GLMM?
Across evaluations, GLMMs consistently ranked higher than GAMs. This is because GLMMs can represent country-specific random effects and temporal autoregression directly, which are crucial for country–month conflict data. GAMs with splines are flexible, but the GLMM structure provided a clearer and more systematic way to capture hierarchical dynamics across countries and over time.
Final choice.
Putting these results together, the Negative Binomial GLMM was selected because it accounted for overdispersion, captured country and temporal dynamics more effectively, and delivered the best overall forecast performance in the validation and test comparisons.
3) Inputs and Outputs
The forecasts are generated at the level of country–month units. In practice, this means that each observation corresponds to a particular country in a particular month—for example, “Nigeria in March 2025.” For every such unit, the model brings together several types of information before producing a forecast.
First, the model anchors each observation in space and time, using identifiers for both the country and the month. This ensures that the model learns patterns that are specific to individual countries and that it can track how risk changes from month to month. Second, the model incorporates information about recent conflict history. Because violence tends to be persistent, the number of fatalities in the previous month is used as a predictor for the current month, allowing the model to capture momentum or recurrence in conflict dynamics. Third, the model draws on a set of background covariates that capture structural conditions linked to conflict. In Patrick’s specification, these included the infant mortality rate (a measure of health and development conditions), military spending as a share of GDP (the relative economic weight of the military), absolute military spending (total resources devoted to the military), and an indicator from V-Dem of whether the military plays a role in executive politics. Together, these three sources of information—the country and time identifiers, the recent conflict history, and the background covariates—give the model a rich set of inputs that combine short-term dynamics with longer-term structural risk factors.
On the output side, the model produces forecasts that are probabilistic rather than deterministic. This means that the forecasts are best understood as distributions of possible outcomes, not as single-point predictions. These distributions can be summarized in three main ways. The first is the point forecast, which gives the mean predicted number of fatalities for a given country–month. For example, the model might forecast that Nigeria in March 2025 will see around 95 fatalities. The second is the cumulative forecast, which aggregates the monthly predictions over a longer horizon—typically three, six, or twelve months. This provides a sense of the projected scale of conflict across the forecast window. The third is the probability of exceeding a threshold, which answers questions such as: what is the chance that fatalities will exceed 25 in a given country during a given period? By repeatedly simulating outcomes from the Negative Binomial distribution, the model can attach explicit probabilities to such threshold events.
Taken together, these outputs move beyond a single best guess. They provide a fuller picture that captures not only the expected level of conflict but also the uncertainty surrounding it and the likelihood of surpassing important thresholds. In this way, the forecasts remain consistent with the Bayesian philosophy that guided the model choice: decision-makers should be equipped with distributions of possible outcomes, not just averages.
4) Codebook
The forecast outputs are delivered as a structured dataset, where each row corresponds to a single country–month observation. Several variables are included to identify the unit and to record the forecasts:
country_id: a numerical identifier for the country.


name: the country’s name.


isoab: the three-letter ISO country code.


outcome_n: the numerical index of the forecast month (counted from the start of the dataset).


dates: the calendar date for the forecasted month.


These variables simply provide the location and timing of the forecast.
The core outputs of the forecasting model are the following:
predicted: the mean forecast of fatalities for that country–month. This is the model’s point prediction, based on averaging across many simulated outcomes drawn from the Negative Binomial GLMM. For example, if the predicted value is 50, the model is saying that across its simulated futures, the expected number of fatalities for that month is about 50. It is important to remember that this is not a guaranteed outcome but the average of a full distribution of possible outcomes.


cumulative_outcome_n: the running total of predicted fatalities over the forecast horizon. This variable adds up the monthly predictions, showing how expected violence accumulates as time advances. For instance, if the monthly predicted values are 10, 15, and 20, the cumulative values for those three months will be 10, 25, and 45. This measure gives a sense of the overall projected scale of conflict rather than focusing only on single months.


outcome_p: the probability that fatalities exceed 25 during the forecast period. This variable translates the distribution of predicted fatalities into the probability of a binary event: “severe conflict” = 1 if deaths ≥25, and 0 otherwise. To calculate it, the model generates many simulated outcomes for each country–month and records how often the threshold of 25 is surpassed. For example, if 720 out of 1,000 simulations are above 25, then outcome_p = 0.72. This measure highlights the risk of entering a high-violence scenario, even when the mean forecast might be lower. It is possible to see cases where the mean predicted fatalities are high but outcome_p is low (indicating a skewed distribution with rare extreme events), or where the mean is modest but outcome_p is high (indicating that much of the distribution lies close to or above the threshold). In short, outcome_p is best read as the model’s estimate of the probability that a country–month will cross into a “severe conflict” category.


Taken together, these variables provide three complementary ways to interpret the forecasts: a point estimate of expected fatalities, a cumulative trajectory of violence over time, and a probability of severe conflict as defined by a threshold exceedance.



