package com.ankurdave.calsquashrankings

import java.time.YearMonth

import com.amazonaws.services.dynamodbv2.AmazonDynamoDBClientBuilder
import com.ankurdave.ttt._
import com.ankurdave.ttt.implicits._
import com.gu.scanamo._

object AllPlayersStats {
  /** Computes [[AllPlayersStats]] by fetching match data from DynamoDB and running TTT. */
  def compute(): AllPlayersStats = {
    val dynamo = AmazonDynamoDBClientBuilder.standard().build()
    val matchTable = Table[MonthMatches]("calsquash-matches-cache")
    println("Scanning dynamodb matches")

    val cache: Seq[MonthMatches] = for {
      result <- Scanamo.exec(dynamo)(matchTable.scan())
    } yield result.right.get

    val matches =
      for {
        MonthMatches(filename, monthMatchesOpt, _) <- cache
        date = filenameToDate(filename)
        monthMatches <- monthMatchesOpt.toSeq
        Match(winnerStr, loserStr, winnerScore) <- monthMatches
        winner = PlayerId(winnerStr)
        loser = PlayerId(loserStr)
      } yield (date, winner, loser, winnerScore)

    val currentPlayers =
      (for {
        MonthMatches(filename, _, currentPlayersOpt) <- cache
        if filename == "current.html"
        currentPlayers <- currentPlayersOpt.toSeq
        pName <- currentPlayers
      } yield PlayerId(pName)).toSet

    // mu and sigma are chosen arbitrarily to resemble the old TrueSkill values and do not
    // affect rankings
    val mu = 15.0
    val sigma = mu / 3.0
    // beta and tau are chosen to maximize the log-evidence over the squash dataset using a
    // parameter sweep, meaning they best model players' observed match-to-match performance
    // variability (beta) and month-to-month change (tau)
    val beta = sigma * 0.37
    val tau = sigma * 0.058
    val skillVariables = new TTT(
      new Games(matchesToGames(matches)),
      mu = mu, sigma = sigma, beta = beta, tau = tau, delta = 0.01).run()

    new AllPlayersStats(matches, skillVariables, currentPlayers)
  }

  private def monthToNumber(month: String) = month match {
    case "jan" | "decjan" => 1
    case "feb" => 2
    case "mar" => 3
    case "apr" => 4
    case "may" => 5
    case "jun" | "june" => 6
    case "jul" | "july" => 7
    case "aug" => 8
    case "sep" | "sept" => 9
    case "oct" => 10
    case "nov" => 11
    case "dec" => 12
  }

  private val currentDate = YearMonth.now()

  private val dateRegex = """^([a-z]+)(\d{2})\.html$""".r

  private def filenameToDate(f: String): YearMonth = f match {
    case "current.html" => currentDate
    case dateRegex(month, year) => YearMonth.of(2000 + year.toInt, monthToNumber(month))
  }

  /** Expands each match into a number of games based on the match score. */
  private def matchesToGames(
    matches: Seq[(YearMonth, PlayerId, PlayerId, Int)]): Seq[Game[YearMonth]] = {
    (for ((date, winner, loser, winnerScore) <- matches) yield (
      Seq.fill(3) { Game(date, winner, loser) }
        ++ Seq.fill(6 - winnerScore) { Game(date, loser, winner) })).flatten
  }
}

/** Holds match history and ratings for all players. */
class AllPlayersStats(
  val matches: Seq[(YearMonth, PlayerId, PlayerId, Int)],
  val skillVariables: Map[(YearMonth, PlayerId), Gaussian],
  val currentPlayers: Set[PlayerId]) {

  /** Converts a YearMonth into an ISO date string for Dynamo. */
  private def str(d: YearMonth): String = d.toString + "-01"

  /** Set of all players. */
  val allPlayers: Set[PlayerId] = (for ((d, w, l, ws) <- matches) yield Seq(w, l)).flatten.toSet

  /** Match history for each player. */
  val playerMatchHistory: Map[PlayerId, Seq[PlayerMatchResult]] =
    (for ((d, w, l, ws) <- matches)
    yield Seq(
      (w, PlayerMatchResult(str(d), l.name, "W", ws)),
      (l, PlayerMatchResult(str(d), w.name, "L", ws))))
      .flatten.groupBy(_._1).mapValues(_.map(_._2).sortBy(_.date))

  /** Rating history for each player. */
  val playerRatingHistory: Map[PlayerId, Seq[Rating]] =
    (for (((d, p), r) <- skillVariables.toSeq)
    yield (p, Rating(str(d), r.mu, r.sigma)))
      .groupBy(_._1).mapValues(_.map(_._2).sortBy(_.date))

  def uploadToDynamo(dryRun: Boolean): Unit = {
    val dynamo = AmazonDynamoDBClientBuilder.standard().build()
    val playerStatsTable = Table[PlayerStats]("calsquash-player-stats")
    val playerStats: Set[PlayerStats] =
      (for {
        p <- allPlayers
        rs = playerRatingHistory(p).sortBy(_.date)
        ms = playerMatchHistory(p).sortBy(_.date)
        s = PlayerStats(p.name, rs, ms)
      } yield s).toSet
    if (!dryRun) {
      Scanamo.exec(dynamo)(playerStatsTable.putAll(playerStats))
    }
  }
}

