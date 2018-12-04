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

    // Construct a Google Charts row (JavaScript array) for each historical player rating and
    // opponent rating
    val playerRatingData =
      for (Rating(date, mu, sigma) <- allPlayersStats.playerRatingHistory(player))
      yield "[new Date(%d, %d, 1), %f, %f, %f, null, null, null, null]".format(
        date.getYear,
        date.getMonthValue - 1,
        mu,
        mu - 3.0 * sigma,
        mu + 3.0 * sigma)

    val opponentRatingData =
      for (PlayerMatchResult(date, opponent, outcome, winner_score, opponent_mu)
        <- allPlayersStats.playerMatchHistory(player))
      yield {
        val rowTemplate =
          outcome match {
            case Won =>  """[new Date(%d, %d, 1), null, null, null, null, null, %f, "%s"]"""
            case Lost => """[new Date(%d, %d, 1), null, null, null, %f, "%s", null, null]"""
          }
        rowTemplate.format(
          date.getYear,
          date.getMonthValue - 1,
          opponent_mu,
          JSONValue.escape(opponent.name))
      }

    val ratingData = (playerRatingData ++ opponentRatingData).mkString(",\n")

    new PlayerStatsPage(player, PageUtils.page(
      player.name,
      frag("statistics for ", span(`class` := "file", player.name)),
      frag(
        script(
          `type` := "text/javascript",
          src := "https://www.gstatic.com/charts/loader.js"),
        script(
          `type` := "text/javascript",
          raw(s"""
            |google.charts.load('current', { 'packages': ['corechart'] });
            |google.charts.setOnLoadCallback(drawChart);
            |window.addEventListener('resize', drawChart);
            |function drawChart() {
            |    var data = new google.visualization.DataTable();
            |    data.addColumn('date', 'Date');
            |    data.addColumn('number', 'Rating');
            |    data.addColumn({ type: 'number', role: 'interval' });
            |    data.addColumn({ type: 'number', role: 'interval' });
            |    data.addColumn('number', 'Winning opponent rating');
            |    data.addColumn({ type: 'string', role: 'tooltip'});
            |    data.addColumn('number', 'Losing opponent rating');
            |    data.addColumn({ type: 'string', role: 'tooltip'});
            |    data.addRows([$ratingData]);
            |    var options = {'chartArea': { 'top': 10, 'right': 20, 'bottom': 40, 'left': 40 },
            |                   'intervals': {
            |                       'style': 'area',
            |                       'color': '#90CAF9',
            |                       'fillOpacity': 0.2 },
            |                   'legend': 'none',
            |                   'series': {
            |                       0: { lineWidth: 2, pointSize: 2, color: '#0D47A1' },
            |                       1: { lineWidth: 0, pointSize: 7, color: '#F57C00',
            |                            pointShape: { type: 'triangle', rotation: 180 }},
            |                       2: { lineWidth: 0, pointSize: 7, color: '#43A047',
            |                            pointShape: 'triangle' }}};
            |    var chart = new google.visualization.LineChart(
            |        document.getElementById('rating_history'));
            |    chart.draw(data, options);
            |}""".stripMargin))),
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
          style := "width:100%;padding-bottom:55%;position:relative",
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
