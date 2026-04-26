#pragma once
#include <Arduino.h>
#include <vector>

class FailsafeQueue {
 public:
  bool push(const String& payload);
  bool pop(String& payload);
  size_t size() const { return queue_.size(); }

 private:
  std::vector<String> queue_;
  static constexpr size_t kMaxQueue = 20;
};
