package com.ankurdave.calsquashrankings

import java.io.File
import java.util.UUID

import org.scalatest.FunSuite

class CalsquashRankingsSuite extends FunSuite {
  def createTempDir(): File = {
    val root = System.getProperty("java.io.tmpdir")
    val namePrefix = "calsquash-rankings"
    val dir = new File(root, namePrefix + "-" + UUID.randomUUID.toString)
    dir.mkdirs()
    dir.getCanonicalFile
  }

  test("new match handler dry run") {
    val outputDir = createTempDir()
    println(s"Saving results to $outputDir")
    new NewMatchHandler().recomputeStats(Some(outputDir))
  }
}
