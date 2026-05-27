import { Route, Routes } from "react-router-dom";
import CustomerView from "./pages/CustomerView.jsx";
import AdminView from "./pages/AdminView.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<CustomerView />} />
      <Route path="/admin" element={<AdminView />} />
    </Routes>
  );
}
