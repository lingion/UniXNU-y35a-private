// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef QCOMSDCARD_TEST_MODEL_H
#define QCOMSDCARD_TEST_MODEL_H

#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <vector>

#include "../SdCardCore.h"

struct SdModel {
  bool present = true;
  bool ready_after = true;
  bool width4 = false;
  bool high_capacity = true;
  uint32_t capacity = 131072;
  uint32_t rca = 0x1234;
  uint32_t ocr = 0xC0FF8000U;
  unsigned acmd41_count = 0;
  std::vector<unsigned> commands;
  std::vector<uint32_t> arguments;
  std::vector<uint8_t> image;

  SdModel() : image(static_cast<size_t>(capacity) * 512U, 0) {
    for (size_t i = 0; i < image.size(); ++i) image[i] = static_cast<uint8_t>(i);
  }

  bool cardPresent() const { return present; }
  void delay() {}
  bool setBusWidth4(uint16_t value) { assert(value == rca); width4 = true; return true; }
  uint32_t capacitySectors() const { return capacity; }
  uint32_t response() const { return last_response; }

  bool command(unsigned index, uint32_t argument, sdcard::Transfer transfer,
               uint8_t *data, unsigned blocks) {
    commands.push_back(index);
    arguments.push_back(argument);
    assert(blocks != 0);
    if (index == 0) { last_response = 0; return true; }
    if (index == 8) { last_response = 0x1aa; return true; }
    if (index == 41) {
      ++acmd41_count;
      last_response = ready_after && acmd41_count >= 2 ? ocr : (ocr & 0x7fffffffU);
      return true;
    }
    if (index == 3) { last_response = rca << 16; return true; }
    if (index == 17 || index == 18) {
      assert(transfer == sdcard::TRANS_READ && data);
      uint32_t sector = high_capacity ? argument : argument / 512U;
      size_t offset = static_cast<size_t>(sector) * 512U;
      size_t bytes = static_cast<size_t>(blocks) * 512U;
      assert(offset + bytes <= image.size());
      memcpy(data, image.data() + offset, bytes);
      last_response = 0;
      return true;
    }
    last_response = 0;
    return true;
  }

 private:
  uint32_t last_response = 0;
};

#endif
