
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

const checkoutData = (() => {
  try {
    return JSON.parse(localStorage.getItem("nexvionCheckout") || "null");
  } catch {
    return null;
  }
})();

function money(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(Number(value) || 0);
}

function escapeHTML(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setFieldError(inputId, errorId, message) {
  const input = $("#" + inputId);
  const error = $("#" + errorId);

  input?.classList.toggle("invalid", Boolean(message));

  if (error) error.textContent = message || "";
}

function onlyDigits(input, maxLength) {
  if (!input) return;

  input.addEventListener("input", () => {
    input.value = input.value.replace(/\D/g, "").slice(0, maxLength);
  });

  input.addEventListener("keydown", (event) => {
    if (
      event.ctrlKey ||
      event.metaKey ||
      [
        "Backspace",
        "Delete",
        "ArrowLeft",
        "ArrowRight",
        "Home",
        "End",
        "Tab"
      ].includes(event.key)
    ) {
      return;
    }

    if (!/^\d$/.test(event.key)) {
      event.preventDefault();
    }
  });

  input.addEventListener("paste", (event) => {
    event.preventDefault();

    const text = event.clipboardData
      .getData("text")
      .replace(/\D/g, "")
      .slice(0, maxLength);

    input.value = text;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function initializeNumberFields() {
  onlyDigits($("#customerPhone"), 10);
  onlyDigits($("#customerPin"), 6);
  onlyDigits($("#cardCvv"), 3);

  const cardNumber = $("#cardNumber");
  if (cardNumber) {
    cardNumber.addEventListener("input", () => {
      const digits = cardNumber.value.replace(/\D/g, "").slice(0, 16);
      cardNumber.value = digits.replace(/(.{4})/g, "$1 ").trim();
    });
  }

  const expiry = $("#cardExpiry");
  if (expiry) {
    expiry.addEventListener("input", () => {
      let digits = expiry.value.replace(/\D/g, "").slice(0, 4);

      if (digits.length > 2) {
        digits = `${digits.slice(0, 2)}/${digits.slice(2)}`;
      }

      expiry.value = digits;
    });
  }
}

function renderOrder() {
  if (!checkoutData || !Array.isArray(checkoutData.items) || !checkoutData.items.length) {
    $("#paymentContent")?.classList.add("hidden");
    $("#paymentEmpty")?.classList.remove("hidden");
    return;
  }

  $("#summaryUser").textContent = checkoutData.user?.name || "Customer";

  $("#orderItems").innerHTML = checkoutData.items.map((item) => `
    <div class="order-item">
      <img
        src="${item.image}"
        alt="${escapeHTML(item.name)}"
        onerror="this.onerror=null;this.src='https://placehold.co/200x200/f1f1ef/222?text=NEXVION';"
      >

      <div>
        <div class="order-item-name">${escapeHTML(item.name)}</div>
        <div class="order-item-meta">Qty: ${Number(item.quantity) || 1}</div>
      </div>

      <div class="order-item-price">
        ${money(Number(item.price) * Number(item.quantity))}
      </div>
    </div>
  `).join("");

  const subtotal = Number(checkoutData.subtotal) || 0;

  $("#summarySubtotal").textContent = money(subtotal);
  $("#summaryTotal").textContent = money(subtotal);

  if (checkoutData.user?.name) {
    $("#customerName").value = checkoutData.user.name;
  }
}

/* --------------------------
   PAYMENT METHOD UI
-------------------------- */

$$('input[name="paymentMethod"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    $$(".method").forEach((card) => {
      card.classList.toggle(
        "active",
        card.querySelector("input")?.checked
      );
    });

    const method = document.querySelector(
      'input[name="paymentMethod"]:checked'
    )?.value;

    $("#upiFields")?.classList.toggle("hidden", method !== "upi");
    $("#cardFields")?.classList.toggle("hidden", method !== "card");
    $("#codFields")?.classList.toggle("hidden", method !== "cod");
  });
});

/* --------------------------
   VALIDATION
-------------------------- */

function validateCustomer() {
  let valid = true;

  const name = $("#customerName").value.trim();
  const phone = $("#customerPhone").value.trim();
  const address = $("#customerAddress").value.trim();
  const city = $("#customerCity").value.trim();
  const pin = $("#customerPin").value.trim();

  if (name.length < 2) {
    setFieldError("customerName", "nameError", "Enter your full name.");
    valid = false;
  } else {
    setFieldError("customerName", "nameError", "");
  }

  if (!/^\d{10}$/.test(phone)) {
    setFieldError("customerPhone", "phoneError", "Enter exactly 10 digits.");
    valid = false;
  } else {
    setFieldError("customerPhone", "phoneError", "");
  }

  if (address.length < 5) {
    setFieldError("customerAddress", "addressError", "Enter your delivery address.");
    valid = false;
  } else {
    setFieldError("customerAddress", "addressError", "");
  }

  if (city.length < 2) {
    setFieldError("customerCity", "cityError", "Enter your city.");
    valid = false;
  } else {
    setFieldError("customerCity", "cityError", "");
  }

  if (!/^\d{6}$/.test(pin)) {
    setFieldError("customerPin", "pinError", "Enter exactly 6 digits.");
    valid = false;
  } else {
    setFieldError("customerPin", "pinError", "");
  }

  return valid;
}

function validatePayment() {
  const method = document.querySelector(
    'input[name="paymentMethod"]:checked'
  )?.value;

  let valid = true;

  if (method === "upi") {
    const upi = $("#upiId").value.trim();

    if (!/^[A-Za-z0-9._-]{2,}@[A-Za-z]{2,}$/.test(upi)) {
      setFieldError("upiId", "upiError", "Enter a valid UPI ID.");
      valid = false;
    } else {
      setFieldError("upiId", "upiError", "");
    }
  }

  if (method === "card") {
    const number = $("#cardNumber").value.replace(/\D/g, "");
    const name = $("#cardName").value.trim();
    const expiry = $("#cardExpiry").value.trim();
    const cvv = $("#cardCvv").value.trim();

    if (!/^\d{16}$/.test(number)) {
      setFieldError("cardNumber", "cardNumberError", "Card number must contain 16 digits.");
      valid = false;
    } else {
      setFieldError("cardNumber", "cardNumberError", "");
    }

    if (name.length < 2) {
      setFieldError("cardName", "cardNameError", "Enter the cardholder name.");
      valid = false;
    } else {
      setFieldError("cardName", "cardNameError", "");
    }

    if (!/^(0[1-9]|1[0-2])\/\d{2}$/.test(expiry)) {
      setFieldError("cardExpiry", "cardExpiryError", "Use MM/YY format.");
      valid = false;
    } else {
      setFieldError("cardExpiry", "cardExpiryError", "");
    }

    if (!/^\d{3}$/.test(cvv)) {
      setFieldError("cardCvv", "cardCvvError", "CVV must contain 3 digits.");
      valid = false;
    } else {
      setFieldError("cardCvv", "cardCvvError", "");
    }
  }

  return valid;
}

/* --------------------------
   SUBMIT
-------------------------- */

$("#paymentForm")?.addEventListener("submit", (event) => {
  event.preventDefault();

  if (!checkoutData?.items?.length) return;

  const customerValid = validateCustomer();
  const paymentValid = validatePayment();

  if (!customerValid || !paymentValid) {
    const invalid = $(".invalid");
    invalid?.focus();
    return;
  }

  const method = document.querySelector(
    'input[name="paymentMethod"]:checked'
  )?.value || "upi";

  const orderId = `NX${Date.now().toString().slice(-8)}`;

  const order = {
    ...checkoutData,
    orderId,
    paymentMethod: method,
    customer: {
      name: $("#customerName").value.trim(),
      phone: $("#customerPhone").value.trim(),
      address: $("#customerAddress").value.trim(),
      city: $("#customerCity").value.trim(),
      pin: $("#customerPin").value.trim()
    },
    createdAt: Date.now()
  };

  localStorage.setItem("nexvionLastOrder", JSON.stringify(order));

  localStorage.removeItem("nexvionCheckout");
  localStorage.removeItem("nexvionCart");
  localStorage.removeItem("davineCart");

  $("#successOrderNumber").textContent = `Order #${orderId}`;

  $("#paymentSuccess").classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
});

document.addEventListener("DOMContentLoaded", () => {
  initializeNumberFields();
  renderOrder();
});
