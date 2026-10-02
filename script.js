
/* ==========================================================
   NEXVION STORE — MAIN FRONTEND JAVASCRIPT
   Demo frontend authentication/cart using localStorage.
========================================================== */

const products = [
  {
    id: 1,
    name: "Aero Chronograph",
    category: "Accessories",
    price: 2999,
    stock: true,
    tag: "BESTSELLER",
    image: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=90"
  },
  {
    id: 2,
    name: "Urban Leather Tote",
    category: "Fashion",
    price: 2499,
    stock: true,
    tag: "NEW",
    image: "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=900&q=90"
  },
  {
    id: 3,
    name: "Studio Headphones",
    category: "Electronics",
    price: 3999,
    stock: true,
    tag: "POPULAR",
    image: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=90"
  },
  {
    id: 4,
    name: "Everyday Sneakers",
    category: "Fashion",
    price: 3299,
    stock: true,
    tag: "SALE",
    image: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=90"
  },
  {
    id: 5,
    name: "Ceramic Desk Set",
    category: "Home",
    price: 1299,
    stock: true,
    tag: "NEW",
    image: "https://images.unsplash.com/photo-1494438639946-1ebd1d20bf85?auto=format&fit=crop&w=900&q=90"
  },
  {
    id: 6,
    name: "Smart Speaker",
    category: "Electronics",
    price: 4499,
    stock: true,
    tag: "SMART",
    image: "https://images.unsplash.com/photo-1589003077984-894e133dabab?auto=format&fit=crop&w=900&q=90"
  },
  {
    id: 7,
    name: "Classic Sunglasses",
    category: "Accessories",
    price: 1799,
    stock: true,
    tag: "TRENDING",
    image: "https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=900&q=90"
  },
  {
    id: 8,
    name: "Linen Home Throw",
    category: "Home",
    price: 1899,
    stock: true,
    tag: "SALE",
    image: "https://images.unsplash.com/photo-1583845112203-454c7b6e6e31?auto=format&fit=crop&w=900&q=90"
  },
  {
    id: 9,
    name: "Minimal Backpack",
    category: "Fashion",
    price: 2199,
    stock: true,
    tag: "NEW",
    image: "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=900&q=90"
  },
  {
    id: 10,
    name: "Premium Camera",
    category: "Electronics",
    price: 4999,
    stock: true,
    tag: "FEATURED",
    image: "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=90"
  },
  {
    id: 11,
    name: "Classic Wallet",
    category: "Accessories",
    price: 999,
    stock: true,
    tag: "POPULAR",
    image: "https://images.unsplash.com/photo-1627123424574-724758594e93?auto=format&fit=crop&w=900&q=90"
  },
  {
    id: 12,
    name: "Modern Table Lamp",
    category: "Home",
    price: 1599,
    stock: true,
    tag: "HOME",
    image: "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=900&q=90"
  }
];

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

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

function toast(message) {
  const box = $("#toast");
  if (!box) return;

  box.textContent = message;
  box.classList.add("show");

  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => {
    box.classList.remove("show");
  }, 2300);
}

/* --------------------------
   STORAGE / MIGRATION
-------------------------- */

function getJSON(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

let cart = getJSON("nexvionCart", getJSON("davineCart", []));
let users = getJSON("nexvionUsers", getJSON("davineUsers", []));
let currentUser = getJSON("nexvionCurrentUser", getJSON("davineCurrentUser", null));

function saveCart() {
  localStorage.setItem("nexvionCart", JSON.stringify(cart));
}

function saveUsers() {
  localStorage.setItem("nexvionUsers", JSON.stringify(users));
}

function saveCurrentUser() {
  if (currentUser) {
    localStorage.setItem("nexvionCurrentUser", JSON.stringify(currentUser));
  } else {
    localStorage.removeItem("nexvionCurrentUser");
  }
}

/* --------------------------
   AUTH
-------------------------- */

function renderAuth() {
  const area = $("#authArea");
  if (!area) return;

  if (currentUser) {
    const firstName = escapeHTML(currentUser.name.split(" ")[0]);

    area.innerHTML = `
      <button class="user-button" id="logoutButton">
        Hi, ${firstName} · Logout
      </button>
    `;

    $("#logoutButton").addEventListener("click", logout);
  } else {
    area.innerHTML = `
      <button class="button button-dark" id="signInButton">
        Sign In
      </button>
    `;

    $("#signInButton").addEventListener("click", () => openAuth("login"));
  }
}

function openAuth(tab = "login") {
  const modal = $("#authModal");
  if (!modal) return;

  modal.classList.add("active");
  modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("no-scroll");
  switchAuth(tab);
}

function closeAuth() {
  const modal = $("#authModal");
  if (!modal) return;

  modal.classList.remove("active");
  modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("no-scroll");
}

function switchAuth(tab) {
  $$(".auth-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.authTab === tab);
  });

  $("#loginForm")?.classList.toggle("hidden", tab !== "login");
  $("#registerForm")?.classList.toggle("hidden", tab !== "register");
}

function logout() {
  currentUser = null;
  saveCurrentUser();
  renderAuth();
  toast("You have been logged out.");
}

$$("[data-close-auth]").forEach((button) => {
  button.addEventListener("click", closeAuth);
});

$$("[data-auth-tab]").forEach((button) => {
  button.addEventListener("click", () => switchAuth(button.dataset.authTab));
});

$$("[data-switch-auth]").forEach((button) => {
  button.addEventListener("click", () => switchAuth(button.dataset.switchAuth));
});

$("#registerForm")?.addEventListener("submit", (event) => {
  event.preventDefault();

  const name = $("#registerName").value.trim();
  const email = $("#registerEmail").value.trim().toLowerCase();
  const password = $("#registerPassword").value;
  const confirmPassword = $("#registerConfirmPassword").value;

  if (name.length < 2) {
    toast("Please enter your full name.");
    return;
  }

  if (password.length < 6) {
    toast("Password must contain at least 6 characters.");
    return;
  }

  if (password !== confirmPassword) {
    toast("Passwords do not match.");
    return;
  }

  if (users.some((user) => user.email === email)) {
    toast("This email is already registered.");
    switchAuth("login");
    $("#loginEmail").value = email;
    return;
  }

  const user = {
    id: Date.now(),
    name,
    email,
    password
  };

  users.push(user);
  currentUser = user;

  saveUsers();
  saveCurrentUser();

  $("#registerForm").reset();
  closeAuth();
  renderAuth();

  toast("Account created successfully.");
});

$("#loginForm")?.addEventListener("submit", (event) => {
  event.preventDefault();

  const email = $("#loginEmail").value.trim().toLowerCase();
  const password = $("#loginPassword").value;

  const user = users.find(
    (item) => item.email === email && item.password === password
  );

  if (!user) {
    toast("Invalid email or password.");
    return;
  }

  currentUser = user;
  saveCurrentUser();

  $("#loginForm").reset();
  closeAuth();
  renderAuth();

  toast(`Welcome back, ${user.name.split(" ")[0]}!`);
});

/* --------------------------
   CART
-------------------------- */

function cartCount() {
  return cart.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
}

function cartTotal() {
  return cart.reduce((sum, item) => {
    const product = products.find((p) => p.id === Number(item.id));
    return product ? sum + product.price * Number(item.quantity || 0) : sum;
  }, 0);
}

function updateCartCount() {
  const count = $("#cartCount");
  if (count) count.textContent = cartCount();
}

function addToCart(id) {
  const product = products.find((item) => item.id === Number(id));

  if (!product) return;

  const existing = cart.find((item) => item.id === product.id);

  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({ id: product.id, quantity: 1 });
  }

  saveCart();
  renderCart();
  updateCartCount();

  toast(`${product.name} added to your bag.`);
}

function changeQuantity(id, amount) {
  const item = cart.find((entry) => entry.id === Number(id));

  if (!item) return;

  item.quantity += amount;

  if (item.quantity <= 0) {
    cart = cart.filter((entry) => entry.id !== Number(id));
  }

  saveCart();
  renderCart();
  updateCartCount();
}

function removeFromCart(id) {
  cart = cart.filter((item) => item.id !== Number(id));

  saveCart();
  renderCart();
  updateCartCount();

  toast("Product removed from your bag.");
}

function renderCart() {
  const container = $("#cartItems");
  if (!container) return;

  if (!cart.length) {
    container.innerHTML = `
      <div style="text-align:center;padding:55px 15px;color:#888;">
        <div style="font-size:38px;margin-bottom:12px;">🛍</div>
        <strong>Your bag is empty.</strong>
        <p style="font-size:11px;margin-top:7px;">Add something you love from the shop.</p>
      </div>
    `;

    if ($("#subtotal")) $("#subtotal").textContent = money(0);
    return;
  }

  container.innerHTML = cart
    .map((item) => {
      const product = products.find((p) => p.id === Number(item.id));

      if (!product) return "";

      return `
        <article class="cart-item">
          <img src="${product.image}" alt="${escapeHTML(product.name)}">

          <div>
            <h4>${escapeHTML(product.name)}</h4>
            <p>${money(product.price)}</p>

            <div class="quantity">
              <button type="button" data-minus="${product.id}">−</button>
              <span>${item.quantity}</span>
              <button type="button" data-plus="${product.id}">+</button>
            </div>
          </div>

          <button type="button" class="remove-item" data-remove="${product.id}">
            Remove
          </button>
        </article>
      `;
    })
    .join("");

  $("#subtotal").textContent = money(cartTotal());

  $$("[data-plus]").forEach((button) => {
    button.addEventListener("click", () =>
      changeQuantity(button.dataset.plus, 1)
    );
  });

  $$("[data-minus]").forEach((button) => {
    button.addEventListener("click", () =>
      changeQuantity(button.dataset.minus, -1)
    );
  });

  $$("[data-remove]").forEach((button) => {
    button.addEventListener("click", () =>
      removeFromCart(button.dataset.remove)
    );
  });
}

function openCart() {
  $("#cartDrawer")?.classList.add("active");
  $("#drawerOverlay")?.classList.add("active");
  document.body.classList.add("no-scroll");
}

function closeCart() {
  $("#cartDrawer")?.classList.remove("active");
  $("#drawerOverlay")?.classList.remove("active");
  document.body.classList.remove("no-scroll");
}

$("#cartButton")?.addEventListener("click", openCart);
$("#closeCart")?.addEventListener("click", closeCart);
$("#drawerOverlay")?.addEventListener("click", closeCart);

/* --------------------------
   CHECKOUT
-------------------------- */

$("#checkoutButton")?.addEventListener("click", () => {
  if (!cart.length) {
    toast("Your bag is empty.");
    return;
  }

  if (!currentUser) {
    closeCart();
    openAuth("login");
    toast("Please sign in before checkout.");
    return;
  }

  const checkoutItems = cart
    .map((item) => {
      const product = products.find((p) => p.id === Number(item.id));
      if (!product) return null;

      return {
        id: product.id,
        name: product.name,
        category: product.category,
        price: product.price,
        image: product.image,
        quantity: Number(item.quantity)
      };
    })
    .filter(Boolean);

  localStorage.setItem(
    "nexvionCheckout",
    JSON.stringify({
      user: {
        id: currentUser.id,
        name: currentUser.name,
        email: currentUser.email
      },
      items: checkoutItems,
      subtotal: cartTotal(),
      createdAt: Date.now()
    })
  );

  closeCart();
  window.location.href = "payment.html";
});

/* --------------------------
   FEATURED PRODUCTS
-------------------------- */

function productCard(product, shop = false) {
  const imageClass = shop ? "shop-product-image" : "product-image";
  const cardClass = shop ? "shop-product-card" : "product-card";
  const infoClass = shop ? "shop-product-info" : "product-info";
  const categoryClass = shop ? "shop-product-category" : "product-category";
  const nameClass = shop ? "shop-product-name" : "product-name";
  const priceClass = shop ? "shop-product-price" : "product-price";
  const buttonClass = shop ? "shop-add-cart" : "add-cart";

  return `
    <article class="${cardClass}">
      <div class="${imageClass}">
        <img
          src="${product.image}"
          alt="${escapeHTML(product.name)}"
          loading="lazy"
          onerror="this.onerror=null;this.src='https://placehold.co/900x900/f1f1ef/222?text=NEXVION';"
        >

        <span class="${shop ? "shop-product-tag" : "product-tag"}">
          ${escapeHTML(product.tag)}
        </span>

        <button
          type="button"
          class="${buttonClass}"
          data-add-cart="${product.id}"
          aria-label="Add ${escapeHTML(product.name)} to bag"
        >
          +
        </button>
      </div>

      <div class="${infoClass}">
        <span class="${categoryClass}">${escapeHTML(product.category)}</span>
        <h3 class="${nameClass}">${escapeHTML(product.name)}</h3>
        <div class="${priceClass}">${money(product.price)}</div>
      </div>
    </article>
  `;
}

function bindAddButtons() {
  $$("[data-add-cart]").forEach((button) => {
    button.addEventListener("click", () =>
      addToCart(button.dataset.addCart)
    );
  });
}

function renderFeaturedProducts() {
  const grid = $("#featuredProducts");
  if (!grid) return;

  grid.innerHTML = products.slice(0, 4).map((p) => productCard(p)).join("");
  bindAddButtons();
}

/* --------------------------
   SHOP FILTERS
-------------------------- */

let selectedCategory = "All";
let selectedPrice = 5000;
let onlyInStock = false;

function renderCategoryFilters() {
  const box = $("#categoryFilters");
  if (!box) return;

  const categories = ["All", ...new Set(products.map((p) => p.category))];

  box.innerHTML = categories
    .map((category) => {
      const count =
        category === "All"
          ? products.length
          : products.filter((p) => p.category === category).length;

      return `
        <button
          type="button"
          class="category-filter ${selectedCategory === category ? "active" : ""}"
          data-category="${escapeHTML(category)}"
        >
          <span>${escapeHTML(category)}</span>
          <span>${count}</span>
        </button>
      `;
    })
    .join("");

  $$("[data-category]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedCategory = button.dataset.category;
      renderCategoryFilters();
      renderShopProducts();
    });
  });
}

function renderShopProducts() {
  const grid = $("#shopProductGrid");
  if (!grid) return;

  const search = ($("#searchInput")?.value || "").trim().toLowerCase();

  let filtered = products.filter((product) => {
    const categoryMatch =
      selectedCategory === "All" ||
      product.category === selectedCategory;

    const priceMatch = product.price <= selectedPrice;
    const stockMatch = !onlyInStock || product.stock;

    const searchMatch =
      !search ||
      product.name.toLowerCase().includes(search) ||
      product.category.toLowerCase().includes(search);

    return categoryMatch && priceMatch && stockMatch && searchMatch;
  });

  const sort = $("#sortProducts")?.value || "featured";

  if (sort === "low") {
    filtered.sort((a, b) => a.price - b.price);
  } else if (sort === "high") {
    filtered.sort((a, b) => b.price - a.price);
  } else if (sort === "name") {
    filtered.sort((a, b) => a.name.localeCompare(b.name));
  }

  if ($("#resultCount")) {
    $("#resultCount").textContent =
      `${filtered.length} ${filtered.length === 1 ? "product" : "products"}`;
  }

  if (!filtered.length) {
    grid.innerHTML = "";
    $("#emptyProducts")?.classList.add("show");
    return;
  }

  $("#emptyProducts")?.classList.remove("show");

  grid.innerHTML = filtered.map((p) => productCard(p, true)).join("");
  bindAddButtons();
}

function loadCategoryFromURL() {
  const category = new URLSearchParams(window.location.search).get("category");

  if (category && products.some((p) => p.category === category)) {
    selectedCategory = category;
  }
}

$("#priceRange")?.addEventListener("input", (event) => {
  selectedPrice = Number(event.target.value);

  $("#maxPriceLabel").textContent =
    selectedPrice >= 5000 ? "₹5,000+" : money(selectedPrice);

  renderShopProducts();
});

$("#inStock")?.addEventListener("change", (event) => {
  onlyInStock = event.target.checked;
  renderShopProducts();
});

$("#sortProducts")?.addEventListener("change", renderShopProducts);

$("#clearFilters")?.addEventListener("click", resetFilters);
$("#emptyClear")?.addEventListener("click", resetFilters);

function resetFilters() {
  selectedCategory = "All";
  selectedPrice = 5000;
  onlyInStock = false;

  if ($("#priceRange")) $("#priceRange").value = "5000";
  if ($("#maxPriceLabel")) $("#maxPriceLabel").textContent = "₹5,000+";
  if ($("#inStock")) $("#inStock").checked = false;
  if ($("#sortProducts")) $("#sortProducts").value = "featured";
  if ($("#searchInput")) $("#searchInput").value = "";

  renderCategoryFilters();
  renderShopProducts();
}

$("#mobileFilterButton")?.addEventListener("click", () => {
  $("#filters")?.classList.toggle("mobile-open");
});

/* --------------------------
   SEARCH
-------------------------- */

$("#searchButton")?.addEventListener("click", () => {
  $("#searchOverlay")?.classList.add("active");
  document.body.classList.add("no-scroll");
  $("#searchInput")?.focus();
});

$("#closeSearch")?.addEventListener("click", closeSearch);

function closeSearch() {
  $("#searchOverlay")?.classList.remove("active");
  document.body.classList.remove("no-scroll");

  if ($("#searchInput")) {
    $("#searchInput").value = "";
  }

  if ($("#shopProductGrid")) {
    renderShopProducts();
  }
}

$("#searchInput")?.addEventListener("input", () => {
  if ($("#shopProductGrid")) renderShopProducts();
});

/* --------------------------
   MOBILE MENU
-------------------------- */

$("#mobileMenuButton")?.addEventListener("click", () => {
  $("#mobileMenu")?.classList.toggle("active");
});

$$(".mobile-menu a").forEach((link) => {
  link.addEventListener("click", () => {
    $("#mobileMenu")?.classList.remove("active");
  });
});

/* --------------------------
   KEYBOARD
-------------------------- */

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;

  closeCart();
  closeAuth();
  closeSearch();
  $("#filters")?.classList.remove("mobile-open");
});

/* --------------------------
   INITIALIZE
-------------------------- */

document.addEventListener("DOMContentLoaded", () => {
  renderAuth();
  renderCart();
  updateCartCount();
  renderFeaturedProducts();

  if ($("#shopProductGrid")) {
    loadCategoryFromURL();
    renderCategoryFilters();
    renderShopProducts();
  }
});
