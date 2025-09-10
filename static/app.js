const { useState, useEffect } = React;

function MenuPage() {
  const [categories, setCategories] = useState([]);
  const [cart, setCart] = useState([]);

  useEffect(() => {
    fetch("/api/menu")
      .then((r) => r.json())
      .then((data) => setCategories(data.categories));
  }, []);

  function addToCart(item) {
    setCart((prev) => {
      const found = prev.find((c) => c.id === item.id);
      if (found) {
        return prev.map((c) =>
          c.id === item.id ? { ...c, qty: c.qty + 1 } : c
        );
      }
      return [...prev, { ...item, qty: 1 }];
    });
  }

  function updateQty(id, qty) {
    setCart((prev) =>
      prev
        .map((c) => (c.id === id ? { ...c, qty } : c))
        .filter((c) => c.qty > 0)
    );
  }

  function getTotal() {
    return cart.reduce((sum, i) => sum + i.price * i.qty, 0).toFixed(2);
  }

  function placeOrder() {
    const car_info = document.getElementById("carInfoInput").value;
    if (cart.length === 0) {
      alert("Cart is empty!");
      return;
    }
    fetch("/api/order", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items: cart, car_info }),
    })
      .then((r) => r.json())
      .then((res) => {
        if (res.order_id) {
          window.history.pushState({}, "", `/order-status/${res.order_id}`);
          window.dispatchEvent(new Event("popstate"));
        }
      });
  }

  return (
    <div className="container-fluid pb-5">
      <div className="row">
        <div className="col-12 col-md-9">
          {categories.map((cat) => (
            <div key={cat.id} className="mb-4">
              <h4 className="text-success">{cat.name}</h4>
              <div className="row">
                {cat.items.map((item) => (
                  <div className="col-6 col-md-4 mb-3" key={item.id}>
                    <div className="card h-100">
                      {item.photo && (
                        <img
                          src={item.photo}
                          className="card-img-top"
                          style={{ maxHeight: "150px", objectFit: "cover" }}
                        />
                      )}
                      <div className="card-body d-flex flex-column">
                        <h6 className="card-title">{item.name}</h6>
                        <p className="card-text small text-muted">
                          ₹{item.price}
                        </p>
                        <button
                          className="btn btn-success btn-sm mt-auto"
                          onClick={() => addToCart(item)}
                        >
                          Add
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* ✅ Desktop Cart (right side) */}
        <div className="d-none d-md-block col-md-3">
          <div className="card shadow-sm sticky-top p-3">
            <h5 className="text-success">Cart</h5>
            {cart.length === 0 ? (
              <p className="small text-muted">Cart is empty</p>
            ) : (
              <div>
                {cart.map((c) => (
                  <div
                    key={c.id}
                    className="d-flex justify-content-between align-items-center mb-2"
                  >
                    <span>
                      {c.name} ×{" "}
                      <input
                        type="number"
                        min="1"
                        value={c.qty}
                        onChange={(e) => updateQty(c.id, parseInt(e.target.value))}
                        style={{ width: "50px" }}
                      />
                    </span>
                    <span>₹{(c.price * c.qty).toFixed(2)}</span>
                  </div>
                ))}
                <input
                  id="carInfoInput"
                  className="form-control my-2"
                  placeholder="Enter Car No. / Info"
                />
                <p><strong>Total:</strong> ₹{getTotal()}</p>
                <button className="btn btn-success w-100" onClick={placeOrder}>
                  Place Order
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ✅ Mobile Cart (bottom panel) */}
      <div className="d-md-none fixed-bottom bg-white border-top shadow-lg p-3">
        {cart.length === 0 ? (
          <p className="small text-muted text-center mb-0">Cart is empty</p>
        ) : (
          <div>
            {cart.map((c) => (
              <div
                key={c.id}
                className="d-flex justify-content-between align-items-center mb-1"
              >
                <span>
                  {c.name} ×{" "}
                  <input
                    type="number"
                    min="1"
                    value={c.qty}
                    onChange={(e) => updateQty(c.id, parseInt(e.target.value))}
                    style={{ width: "40px" }}
                  />
                </span>
                <span>₹{(c.price * c.qty).toFixed(2)}</span>
              </div>
            ))}
            <input
              id="carInfoInput"
              className="form-control my-2"
              placeholder="Enter Car No. / Info"
            />
            <div className="d-flex justify-content-between align-items-center mb-2">
              <strong>Total: ₹{getTotal()}</strong>
              <span>{cart.reduce((s, c) => s + c.qty, 0)} items</span>
            </div>
            <button className="btn btn-success w-100" onClick={placeOrder}>
              Place Order
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function OrderStatusPage({ orderId }) {
  const [order, setOrder] = useState(null);

  useEffect(() => {
    fetch(`/api/order/${orderId}`)
      .then((r) => r.json())
      .then((data) => setOrder(data));

    const socket = io("/");
    socket.on("order_update", (msg) => {
      if (msg.order_id == orderId) {
        setOrder((prev) => ({ ...prev, status: msg.status }));
      }
    });
  }, [orderId]);

  if (!order) return <p>Loading...</p>;

  return (
    <div className="container py-4">
      <h3 className="text-success mb-3">Order Status</h3>
      <div className="card p-3 shadow-sm">
        <h5>Order #{order.id}</h5>
        <p><strong>Status:</strong> {order.status}</p>
        <p>
          <strong>Items:</strong>{" "}
          {order.items.map((i) => `${i.qty || i.quantity}× ${i.name}`).join(", ")}
        </p>
        <p><strong>Total:</strong> ₹{order.total}</p>
        <p><strong>Car Info:</strong> {order.car_info || "-"}</p>
        <p>
          <strong>Placed At:</strong>{" "}
          {new Date(order.created_at).toLocaleString()}
        </p>
      </div>
    </div>
  );
}

function App() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const handler = () => setPath(window.location.pathname);
    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  }, []);

  if (path.startsWith("/order-status/")) {
    const orderId = path.split("/").pop();
    return <OrderStatusPage orderId={orderId} />;
  }
  return <MenuPage />;
}

// document.addEventListener("DOMContentLoaded", () => {
//   const root = document.getElementById("root");
//   const orderRoot = document.getElementById("order-status-root");

//   if (orderRoot) {
//     const orderId = orderRoot.getAttribute("data-order-id");
//     ReactDOM.render(<OrderStatusPage orderId={orderId} />, orderRoot);
//   } else if (root) {
//     ReactDOM.render(<App />, root);
//   }
// });


ReactDOM.render(<App />, document.getElementById("root"));
