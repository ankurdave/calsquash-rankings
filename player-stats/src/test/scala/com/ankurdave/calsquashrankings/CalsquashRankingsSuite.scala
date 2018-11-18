package com.ankurdave.calsquashrankings

import org.scalatest.FunSuite

class CalsquashRankingsSuite extends FunSuite {
  test("new match handler dry run") {
    new NewMatchHandler().recomputeStats(dryRun = true)
  }
}
