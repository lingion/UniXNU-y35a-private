// SPDX-License-Identifier: BSD-2-Clause-Patent
// Host acceptance for the removable TF-card protocol core.
// Build: c++ -std=c++17 -Wall -Wextra -Werror Test/sdcard_host.cpp -o sdcard_host_test
#include <assert.h>
#include <stdio.h>

#include "Model.h"

static void require_subsequence(const SdModel &m, const unsigned *wanted, size_t n) {
  size_t at = 0;
  for (unsigned command : m.commands) {
    if (at < n && command == wanted[at]) ++at;
  }
  assert(at == n);
}

int main() {
  {
    SdModel model;
    sdcard::Controller<SdModel> card(model);
    assert(card.init());
    assert(card.ready());
    assert(card.info().high_capacity);
    assert(card.info().four_bit);
    assert(card.info().rca == 0x1234);
    assert(model.acmd41_count == 2);
    const unsigned init_sequence[] = {0, 8, 55, 41, 55, 41, 2, 3, 7};
    require_subsequence(model, init_sequence, sizeof(init_sequence) / sizeof(init_sequence[0]));
    puts("1. SD init, OCR readiness, RCA, and 4-bit switch: ok");
  }

  {
    SdModel model;
    sdcard::Controller<SdModel> card(model);
    assert(card.init());
    uint8_t data[4 * 512] = {};
    assert(card.readSectors(3, 4, data));
    assert(data[0] == model.image[3 * 512]);
    assert(data[4 * 512 - 1] == model.image[6 * 512 - 1]);
    assert(model.commands.back() == 12);
    puts("2. CMD18 block read with CMD12 stop: ok");
  }

  {
    SdModel model;
    model.present = false;
    sdcard::Controller<SdModel> card(model);
    assert(!card.init() && card.error == 1);
    assert(model.commands.empty());
    puts("3. card-detect refusal before command traffic: ok");
  }

  {
    SdModel model;
    model.ready_after = false;
    sdcard::Controller<SdModel> card(model);
    assert(!card.init() && card.error == 4);
    assert(model.acmd41_count == 100);
    puts("4. bounded ACMD41 timeout: ok");
  }

  puts("SdCard protocol host suite: all checks passed");
}
