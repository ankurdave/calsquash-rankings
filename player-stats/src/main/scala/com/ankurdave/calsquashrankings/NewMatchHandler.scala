package com.ankurdave.calsquashrankings

import com.amazonaws.services.lambda.runtime.{Context, RequestHandler}
import scalatags.Text.all._

/** An empty Java type for the Lambda request handler. */
class EmptyType()

/**
 * Recomputes and uploads player stats and leaderboard to DynamoDB and S3. Intended to be run each
 * time a new match is added.
 */
class NewMatchHandler() extends RequestHandler[EmptyType, String] {
  override def handleRequest(input: EmptyType, context: Context): String = {
    recomputeStats(dryRun = false)
	"Success"
  }

  def recomputeStats(dryRun: Boolean): Unit = {
    val allPlayersStats = AllPlayersStats.compute()

    allPlayersStats.uploadToDynamo(dryRun)

    val leaderboardAll = Leaderboard(
      allPlayersStats.allPlayers,
      allPlayersStats,
      "rankings-all.html",
      frag(
        "Rankings for all players. See ",
        a(href := "rankings-current.html", "current players"), "."))
    leaderboardAll.uploadToS3(dryRun)

    val leaderboardCurrent = Leaderboard(
      allPlayersStats.currentPlayers,
      allPlayersStats,
      "rankings-current.html",
      span(
        "Rankings for current box league players. See ",
        a(href := "rankings-all.html", "all players"), "."))
    leaderboardCurrent.uploadToS3(dryRun)
  }
}
