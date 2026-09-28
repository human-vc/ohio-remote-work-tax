suppressMessages(library(HonestDiD))
run <- function(tag) {
  b <- read.csv(sprintf("output/revenue/model_%s_beta.csv", tag), row.names = 1)
  V <- as.matrix(read.csv(sprintf("output/revenue/model_%s_vcv.csv", tag), row.names = 1))
  yrs <- as.integer(sub("Gain_", "", rownames(b)))
  ord <- order(yrs); betahat <- b$coef[ord]; sigma <- V[ord, ord]; yrs <- yrs[ord]
  nPre <- sum(yrs < 2019); nPost <- sum(yrs > 2019)
  post <- yrs[yrs > 2019]; l <- as.numeric(post %in% c(2022, 2023, 2024)) / 3
  orig <- constructOriginalCS(betahat = betahat, sigma = sigma, numPrePeriods = nPre, numPostPeriods = nPost, l_vec = l)
  rm <- createSensitivityResults_relativeMagnitudes(betahat = betahat, sigma = sigma, numPrePeriods = nPre,
          numPostPeriods = nPost, l_vec = l, Mbarvec = seq(0, 2, by = 0.25))
  sd <- createSensitivityResults(betahat = betahat, sigma = sigma, numPrePeriods = nPre, numPostPeriods = nPost,
          l_vec = l, Mvec = seq(0, 0.2, by = 0.025))
  est <- sum(l * betahat[(nPre + 1):(nPre + nPost)])
  cat("\n=====", tag, " pre years:", paste(yrs[yrs < 2019], collapse = ","), " estimate:", round(est, 3), "\n")
  cat("original 95% CI:", round(orig$lb, 3), round(orig$ub, 3), "\n")
  print(as.data.frame(rm)[, c("Mbar", "lb", "ub")], digits = 3)
  print(as.data.frame(sd)[, c("M", "lb", "ub")], digits = 3)
  out <- rbind(data.frame(version = tag, restriction = "relative magnitudes", bound = rm$Mbar, lb = rm$lb, ub = rm$ub),
               data.frame(version = tag, restriction = "smoothness", bound = sd$M, lb = sd$lb, ub = sd$ub),
               data.frame(version = tag, restriction = "original", bound = NA, lb = orig$lb, ub = orig$ub))
  out$estimate <- est
  out
}
res <- do.call(rbind, lapply(c("main", "p85_2016", "p85_2012"), run))
write.csv(res, "output/revenue/honestdid_sensitivity.csv", row.names = FALSE)
out <- list()
for (tag in c("p85_2016", "p85_2012")) {
  b <- read.csv(sprintf("output/revenue/model_%s_beta.csv", tag), row.names = 1); V <- as.matrix(read.csv(sprintf("output/revenue/model_%s_vcv.csv", tag), row.names = 1))
  yrs <- as.integer(sub("Gain_", "", rownames(b))); o <- order(yrs); bh <- b$coef[o]; S <- V[o, o]; yrs <- yrs[o]
  nPre <- sum(yrs < 2019); nPost <- sum(yrs > 2019); l <- as.numeric(yrs[yrs > 2019] %in% 2022:2024) / 3
  pre <- c(bh[1:nPre], 0); cat(tag, "largest consecutive pre-period change:", round(max(abs(diff(pre))), 3), "\n")
  rm <- createSensitivityResults_relativeMagnitudes(betahat = bh, sigma = S, numPrePeriods = nPre, numPostPeriods = nPost, l_vec = l, Mbarvec = seq(0, 0.25, by = 0.025))
  print(as.data.frame(rm)[, c("Mbar", "lb", "ub")], digits = 3)
  out[[tag]] <- data.frame(version = tag, Mbar = rm$Mbar, lb = rm$lb, ub = rm$ub)
}
write.csv(do.call(rbind, out), "output/revenue/honestdid_breakdown.csv", row.names = FALSE)
