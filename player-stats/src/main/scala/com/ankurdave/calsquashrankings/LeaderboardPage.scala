package com.ankurdave.calsquashrankings

import java.io.ByteArrayInputStream
import java.io.File
import java.time.LocalDateTime
import java.time.YearMonth
import java.time.ZoneId
import java.time.format.DateTimeFormatter

import com.amazonaws.services.s3.AmazonS3ClientBuilder
import com.amazonaws.services.s3.model.ObjectMetadata
import com.amazonaws.services.s3.model.PutObjectRequest
import com.ankurdave.ttt._
import scalatags.Text.all._

object LeaderboardPage {
  /** Generates HTML for a leaderboard page containing the given set of players. */
  def apply(
      players: Set[PlayerId], allPlayersStats: AllPlayersStats, filename: String, description: Frag)
    : LeaderboardPage = {
    val entries =
      (for {
        p <- players
        if allPlayersStats.playerMatchHistory.contains(p)
        numMatches = allPlayersStats.playerMatchHistory(p).size
        curSkill = allPlayersStats.playerRatingHistory(p).last
        lastMonthDate = currentDate.minusMonths(1)
        lastMonthSkill = allPlayersStats.skillVariables.get((lastMonthDate, p))
        lastYearDate = currentDate.minusMonths(12)
        lastYearSkill = allPlayersStats.skillVariables.get((lastYearDate, p))
      } yield (
        p, curSkill, numMatches,
        skillDeltaToString(curSkill, lastMonthSkill),
        skillDeltaToString(curSkill, lastYearSkill)))
        .toSeq.sortBy(_._2.mu).reverse

    new LeaderboardPage(
      filename,
      PageUtils.page(
        htmlTitle = filename,
        pageTitle = span(`class` := "file", filename),
        headers = frag(),
        content = frag(
          p(description),
          p("Generated %s.".format(
            LocalDateTime.now(ZoneId.of("America/Los_Angeles"))
              .format(DateTimeFormatter.ofPattern("yyyy-MM-dd h:mm a")))),
          table(
            tr(
              th("Rank"),
              th("Player"),
              th("Skill"),
              th("# Matches"),
              th("1-mo \u0394 Skill"),
              th("12-mo \u0394 Skill")),
            for (((p, curSkill, numMatches, skillDelta1Mo, skillDelta12Mo), i)
              <- entries.zipWithIndex)
            yield tr(
              td(i + 1, `class` := "numeric"),
              td(a(href := "player-stats/" + PageUtils.playerStatsFilename(p), p.name)),
              td(skillToString(curSkill), `class` := "numeric"),
              td(numMatches, `class` := "numeric"),
              td(skillDelta1Mo, `class` := "numeric"),
              td(skillDelta12Mo, `class` := "numeric"))))))
  }

  /** Converts a Rating to a string representing its mean. */
  private def skillToString(skill: Rating): String = "%.2f".format(skill.mu)

  /** 
   * Subtracts a skill from a Rating and converts the difference to a string representing the
   * difference in means.
   */
  private def skillDeltaToString(skillA: Rating, skillBOpt: Option[Gaussian]): String =
    skillBOpt match {
      case Some(skillB) if math.abs(skillA.mu - skillB.mu) >= 0.01 =>
        "%+.2f".format(skillA.mu - skillB.mu).replace("-", "\u2212")
      case _ => ""
    }

  private val currentDate = YearMonth.now()
}

/** Holds a rendered HTML leaderboard for a subset of players. */
class LeaderboardPage(filename: String, html: String) {
  def uploadToS3(outputDir: Option[File]): Unit = {
    val bucket = "ankurdave.com"
    val s3 = AmazonS3ClientBuilder.standard().build()
    val key = s"calsquash-rankings/$filename"
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
        val out = new PrintWriter(new File(dir, filename));
        out.println(html)
        out.close()
    }
  }
}
