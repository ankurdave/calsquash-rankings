package com.ankurdave.calsquashrankings

import java.io.ByteArrayInputStream
import java.io.File
import java.time.format.DateTimeFormatter
import java.util.Locale

import com.amazonaws.services.s3.AmazonS3ClientBuilder
import com.amazonaws.services.s3.model.ObjectMetadata
import com.amazonaws.services.s3.model.PutObjectRequest
import com.ankurdave.ttt._
import org.json.simple.JSONValue
import scalatags.Text.all._

object PlayerStatsPage {
  /** Generates HTML for a player stats page for the given player. */
  def apply(player: PlayerId, allPlayersStats: AllPlayersStats): PlayerStatsPage = {
    val numMatches = allPlayersStats.playerMatchHistory(player).size

    val monthYearFormat = DateTimeFormatter.ofPattern("MMM yyyy").withLocale(Locale.US)

    val matchHistoryTable =
      table(
        `class` := "full-width",
        tr(
          th("Date", `class` := "numeric-heading"),
          th("Opponent"),
          th("Outcome", `class` := "numeric-heading")),
        for (PlayerMatchResult(date, opponent, outcome, winner_score, _)
          <- allPlayersStats.playerMatchHistory(player).reverse)
        yield tr(
          td(date.format(monthYearFormat), `class` := "numeric"),
          td(a(href := PageUtils.playerStatsFilename(opponent), opponent.name)),
          td("%s 3\u2013%d".format(outcome.toString, 6 - winner_score), `class` := "numeric")))

    // Construct a JavaScript array for each historical player rating and opponent rating
    val playerRatingData =
      for (Rating(date, mu, sigma) <- allPlayersStats.playerRatingHistory(player))
      yield "[new Date(%d, %d, 1), %f, %f, %f]".format(
        date.getYear,
        date.getMonthValue - 1,
        mu,
        mu - 3.0 * sigma,
        mu + 3.0 * sigma)

    val opponentRatingData =
      for (PlayerMatchResult(date, opponent, outcome, winner_score, opponent_mu)
        <- allPlayersStats.playerMatchHistory(player))
      yield (outcome, """[new Date(%d, %d, 1), %f, "%s"]""".format(
        date.getYear,
        date.getMonthValue - 1,
        opponent_mu,
        JSONValue.escape(opponent.name)))
    val (winData, lossData) = opponentRatingData.partition(_._1 == Won)

    val skillHistoryJSON = playerRatingData.mkString(",\n")
    val winsJSON = winData.map(_._2).mkString(",\n")
    val lossesJSON = lossData.map(_._2).mkString(",\n")

    new PlayerStatsPage(player, PageUtils.page(
      player.name,
      frag("statistics for ", span(`class` := "file", player.name)),
      frag(
        script(
          `type` := "text/javascript",
          src := "https://code.jquery.com/jquery-3.3.1.min.js"),
        script(
          `type` := "text/javascript",
          src := "https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.1.3/js/bootstrap.bundle.min.js"),
        script(
          `type` := "text/javascript",
          src := "https://d3js.org/d3.v5.min.js"),
        script(
          `type` := "text/javascript",
          src := "https://d3js.org/d3-shape.v1.min.js"),
        script(
          `type` := "text/javascript",
          src := "player-stats-chart.js"),
        script(
          `type` := "text/javascript",
          raw(s"""
            |var skillHistory = [$skillHistoryJSON];
            |var wins = [$winsJSON];
            |var losses = [$lossesJSON];
            |function draw() {
            |    renderPlayerStats(skillHistory, wins, losses);
            |}
            |$$(document).ready(draw);
            |window.addEventListener("resize", draw);
            |""".stripMargin))),
      frag(
        p(
          "See rankings for ",
          a(href := "../rankings-current.html", "current players"),
          " and ",
          a(href := "../rankings-all.html", "all players"),
          "."),

        h2("Rating History"),
        div(
          `class` := "full-width",
          style := "padding-bottom:55%;position:relative",
          div(
            id := "rating_history",
            style := "position:absolute;top:0;bottom:0;left:0;right:0;")),

        h2("Match History"),
        p(s"$numMatches matches"),
        matchHistoryTable)))
  }
}

class PlayerStatsPage(player: PlayerId, html: String) {
  def uploadToS3(outputDir: Option[File]): Unit = {
    val bucket = "ankurdave.com"
    val s3 = AmazonS3ClientBuilder.standard().build()
    val key = "calsquash-rankings/player-stats/%s".format(
      PageUtils.playerStatsFilename(player))
    val htmlBytes = html.getBytes("UTF-8")
    val is = new ByteArrayInputStream(htmlBytes)
    val metadata = new ObjectMetadata
    metadata.setContentType("text/html")
    metadata.setContentLength(htmlBytes.length)
    metadata.setCacheControl("no-cache")
    val req = new PutObjectRequest(bucket, key, is, metadata)
    println("%s -> s3://%s/%s".format(key, bucket, key))
    outputDir match {
      case None =>
        s3.putObject(req)
      case Some(dir) =>
        import java.io.PrintWriter
        val filename = PageUtils.playerStatsFilename(player)
        val out = new PrintWriter(new File(dir, filename));
        out.println(html)
        out.close()
    }
  }
}
