package com.ankurdave.calsquashrankings

import java.io.File
import java.util.concurrent.Executors

import scala.concurrent.Await
import scala.concurrent.ExecutionContext
import scala.concurrent.Future
import scala.concurrent.duration.Duration

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
    recomputeStats(None)
	"Success"
  }

  def recomputeStats(outputDir: Option[File]): Unit = {
    val allPlayersStats = AllPlayersStats.compute()

    val leaderboardAll = LeaderboardPage(
      allPlayersStats.allPlayers,
      allPlayersStats,
      "rankings-all.html",
      frag(
        "Rankings for all players. See ",
        a(href := "rankings-current.html", "current players"), "."))
    leaderboardAll.uploadToS3(outputDir)

    val leaderboardCurrent = LeaderboardPage(
      allPlayersStats.currentPlayers,
      allPlayersStats,
      "rankings-current.html",
      span(
        "Rankings for current box league players. See ",
        a(href := "rankings-all.html", "all players"), "."))
    leaderboardCurrent.uploadToS3(outputDir)

    // Upload the player stats to S3 in parallel
    implicit val ec = ExecutionContext.fromExecutor(Executors.newFixedThreadPool(32))
    val futures =
      for (p <- allPlayersStats.allPlayers) yield Future {
        PlayerStatsPage(p, allPlayersStats).uploadToS3(outputDir)
      }
    Await.result(Future.sequence(futures), Duration.Inf)
  }
}
