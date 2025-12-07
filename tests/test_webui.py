import pytest
from fastapi.testclient import TestClient
from io import BytesIO

try:
    from webui.app import app

except ModuleNotFoundError:
    import sys
    import os  # noqa: F811

    sys.path.insert(
        0,
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")),
    )
    from webui.app import app

client = TestClient(app)


class TestRootEndpoint:

    def test_root_returns_html(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "HAWK" in response.text
        assert "PQC" in response.text


class TestKeyGeneration:

    def test_generate_keys_default_params(self):
        response = client.post(
            "/api/generate-keys",
            data={"seed": 0, "param": "hawk-512", "visualize": False},
        )
        assert response.status_code == 200
        data = response.json()

        assert "public_key" in data
        assert "private_key" in data
        assert "public_key_size" in data
        assert "private_key_size" in data
        assert "steps" in data

        assert isinstance(data["public_key"], str)
        assert isinstance(data["private_key"], str)
        assert len(data["public_key"]) > 0
        assert len(data["private_key"]) > 0

        assert data["public_key_size"] == len(
            bytes.fromhex(data["public_key"])
        )
        assert data["private_key_size"] == len(
            bytes.fromhex(data["private_key"])
        )

    def test_generate_keys_with_seed(self):
        response1 = client.post(
            "/api/generate-keys",
            data={"seed": 0, "param": "hawk-512", "visualize": False},
        )
        response2 = client.post(
            "/api/generate-keys",
            data={"seed": 42, "param": "hawk-512", "visualize": False},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        assert data1["public_key"] != data2["public_key"]
        assert data1["private_key"] != data2["private_key"]

    def test_generate_keys_with_visualization(self):
        response = client.post(
            "/api/generate-keys",
            data={"seed": 0, "param": "hawk-512", "visualize": True},
        )
        assert response.status_code == 200
        data = response.json()

        assert "steps" in data
        assert len(data["steps"]) > 0

        for step in data["steps"]:
            assert "step" in step
            assert "name" in step
            assert "code" in step
            assert "variables" in step
            assert isinstance(step["step"], int)
            assert isinstance(step["name"], str)
            assert isinstance(step["variables"], dict)

    def test_generate_keys_invalid_param(self):
        response = client.post(
            "/api/generate-keys",
            data={"seed": 0, "param": "hawk-256", "visualize": False},
        )
        assert response.status_code == 500
        assert "Only HAWK-512" in response.json()["detail"]

    def test_generate_keys_deterministic(self):
        response1 = client.post(
            "/api/generate-keys",
            data={"seed": 123, "param": "hawk-512", "visualize": False},
        )
        response2 = client.post(
            "/api/generate-keys",
            data={"seed": 123, "param": "hawk-512", "visualize": False},
        )

        data1 = response1.json()
        data2 = response2.json()

        assert data1["public_key"] == data2["public_key"]
        assert data1["private_key"] == data2["private_key"]


class TestSigning:

    @pytest.fixture
    def keypair(self):
        response = client.post(
            "/api/generate-keys",
            data={"seed": 0, "param": "hawk-512", "visualize": False},
        )
        return response.json()

    def test_sign_message_text(self, keypair):
        response = client.post(
            "/api/sign",
            data={
                "message": "Hello, HAWK PQC!",
                "private_key": keypair["private_key"],
                "seed": 0,
                "visualize": False,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert "signature" in data
        assert "signature_size" in data
        assert "message_size" in data
        assert "steps" in data

        assert isinstance(data["signature"], str)
        assert data["signature_size"] > 0
        assert data["message_size"] == len("Hello, HAWK PQC!".encode())

    def test_sign_message_with_visualization(self, keypair):
        response = client.post(
            "/api/sign",
            data={
                "message": "Test message",
                "private_key": keypair["private_key"],
                "seed": 0,
                "visualize": True,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["steps"]) > 0

        # Check for key steps in visualization
        step_names = [step["name"] for step in data["steps"]]
        assert any(
            "Parse" in name or "Secret Key" in name for name in step_names
        )
        assert any("Salt" in name for name in step_names)
        assert any(
            "Signature" in name or "Final" in name for name in step_names
        )

    def test_sign_missing_message(self, keypair):
        response = client.post(
            "/api/sign",
            data={
                "private_key": keypair["private_key"],
                "seed": 0,
                "visualize": False,
            },
        )
        assert response.status_code == 500
        assert "No message provided" in response.json()["detail"]

    def test_sign_missing_private_key(self):
        response = client.post(
            "/api/sign",
            data={"message": "Test", "seed": 0, "visualize": False},
        )
        assert response.status_code == 500
        assert "No private key provided" in response.json()["detail"]

    def test_sign_invalid_private_key(self):
        response = client.post(
            "/api/sign",
            data={
                "message": "Test",
                "private_key": "invalid_hex",
                "seed": 0,
                "visualize": False,
            },
        )
        assert response.status_code == 500

    def test_sign_with_file_upload(self, keypair):
        message_content = b"File uploaded message"

        response = client.post(
            "/api/sign",
            data={
                "private_key": keypair["private_key"],
                "seed": 0,
                "visualize": False,
            },
            files={
                "message_file": (
                    "test.txt",
                    BytesIO(message_content),
                    "text/plain",
                )
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message_size"] == len(message_content)


class TestVerification:

    @pytest.fixture
    def signed_message(self):
        # Generate keys
        keygen_response = client.post(
            "/api/generate-keys",
            data={"seed": 0, "param": "hawk-512", "visualize": False},
        )
        keys = keygen_response.json()

        message = "Test message for verification"
        sign_response = client.post(
            "/api/sign",
            data={
                "message": message,
                "private_key": keys["private_key"],
                "seed": 0,
                "visualize": False,
            },
        )
        sig_data = sign_response.json()

        return {
            "message": message,
            "public_key": keys["public_key"],
            "signature": sig_data["signature"],
        }

    def test_verify_valid_signature(self, signed_message):
        response = client.post(
            "/api/verify",
            data={
                "message": signed_message["message"],
                "public_key": signed_message["public_key"],
                "signature": signed_message["signature"],
                "visualize": False,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert "valid" in data
        assert data["valid"] is True
        assert "message_size" in data
        assert "signature_size" in data
        assert "steps" in data

    def test_verify_invalid_signature_tampered_message(self, signed_message):
        response = client.post(
            "/api/verify",
            data={
                "message": "Tampered message",
                "public_key": signed_message["public_key"],
                "signature": signed_message["signature"],
                "visualize": False,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False

    def test_verify_invalid_signature_wrong_signature(self, signed_message):
        wrong_sig = "00" * 100

        response = client.post(
            "/api/verify",
            data={
                "message": signed_message["message"],
                "public_key": signed_message["public_key"],
                "signature": wrong_sig,
                "visualize": False,
            },
        )
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            assert response.json()["valid"] is False

    def test_verify_with_visualization(self, signed_message):
        response = client.post(
            "/api/verify",
            data={
                "message": signed_message["message"],
                "public_key": signed_message["public_key"],
                "signature": signed_message["signature"],
                "visualize": True,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["steps"]) > 0

        step_names = [step["name"] for step in data["steps"]]
        assert any(
            "Parse" in name or "Signature" in name for name in step_names
        )
        assert any("Salt" in name or "Extract" in name for name in step_names)
        assert any(
            "Verification" in name or "Result" in name for name in step_names
        )

    def test_verify_missing_message(self, signed_message):
        response = client.post(
            "/api/verify",
            data={
                "public_key": signed_message["public_key"],
                "signature": signed_message["signature"],
                "visualize": False,
            },
        )
        assert response.status_code == 500
        assert "No message provided" in response.json()["detail"]

    def test_verify_missing_public_key(self, signed_message):
        response = client.post(
            "/api/verify",
            data={
                "message": signed_message["message"],
                "signature": signed_message["signature"],
                "visualize": False,
            },
        )
        assert response.status_code == 500
        assert "No public key provided" in response.json()["detail"]

    def test_verify_missing_signature(self, signed_message):
        response = client.post(
            "/api/verify",
            data={
                "message": signed_message["message"],
                "public_key": signed_message["public_key"],
                "visualize": False,
            },
        )
        assert response.status_code == 500
        assert "No signature provided" in response.json()["detail"]


class TestEndToEndWorkflow:

    def test_complete_workflow_text_message(self):
        keygen_response = client.post(
            "/api/generate-keys",
            data={"seed": 42, "param": "hawk-512", "visualize": False},
        )
        assert keygen_response.status_code == 200
        keys = keygen_response.json()

        message = "This is a test message for end-to-end workflow"
        sign_response = client.post(
            "/api/sign",
            data={
                "message": message,
                "private_key": keys["private_key"],
                "seed": 42,
                "visualize": False,
            },
        )
        assert sign_response.status_code == 200
        sig_data = sign_response.json()

        verify_response = client.post(
            "/api/verify",
            data={
                "message": message,
                "public_key": keys["public_key"],
                "signature": sig_data["signature"],
                "visualize": False,
            },
        )
        assert verify_response.status_code == 200
        verify_data = verify_response.json()

        assert verify_data["valid"] is True

    def test_complete_workflow_with_visualization(self):
        keygen_response = client.post(
            "/api/generate-keys",
            data={"seed": 0, "param": "hawk-512", "visualize": True},
        )
        keys = keygen_response.json()
        assert len(keys["steps"]) > 0

        message = "Visualization test"
        sign_response = client.post(
            "/api/sign",
            data={
                "message": message,
                "private_key": keys["private_key"],
                "seed": 0,
                "visualize": True,
            },
        )
        sig_data = sign_response.json()
        assert len(sig_data["steps"]) > 0

        verify_response = client.post(
            "/api/verify",
            data={
                "message": message,
                "public_key": keys["public_key"],
                "signature": sig_data["signature"],
                "visualize": True,
            },
        )
        verify_data = verify_response.json()
        assert len(verify_data["steps"]) > 0
        assert verify_data["valid"] is True

    def test_multiple_messages_same_keypair(self):
        keygen_response = client.post(
            "/api/generate-keys",
            data={"seed": 100, "param": "hawk-512", "visualize": False},
        )
        keys = keygen_response.json()

        messages = [
            "First message",
            "Second message",
            "Third message with more content",
        ]

        signatures = []
        for msg in messages:
            sign_response = client.post(
                "/api/sign",
                data={
                    "message": msg,
                    "private_key": keys["private_key"],
                    "seed": 100,
                    "visualize": False,
                },
            )
            assert sign_response.status_code == 200
            signatures.append(sign_response.json()["signature"])

        assert len(set(signatures)) == len(signatures)

        for msg, sig in zip(messages, signatures):
            verify_response = client.post(
                "/api/verify",
                data={
                    "message": msg,
                    "public_key": keys["public_key"],
                    "signature": sig,
                    "visualize": False,
                },
            )
            assert verify_response.json()["valid"] is True


class TestVisualizationContent:

    def test_keygen_visualization_contains_seed(self):
        response = client.post(
            "/api/generate-keys",
            data={"seed": 999, "param": "hawk-512", "visualize": True},
        )
        data = response.json()

        found_seed = False
        for step in data["steps"]:
            if "variables" in step and "seed" in step["variables"]:
                assert step["variables"]["seed"] == 999
                found_seed = True
                break

        assert found_seed, "Seed not found in visualization"

    def test_sign_visualization_contains_salt(self):
        keygen_response = client.post(
            "/api/generate-keys",
            data={"seed": 0, "param": "hawk-512", "visualize": False},
        )
        keys = keygen_response.json()

        response = client.post(
            "/api/sign",
            data={
                "message": "Test",
                "private_key": keys["private_key"],
                "seed": 0,
                "visualize": True,
            },
        )
        data = response.json()

        found_salt = False
        for step in data["steps"]:
            if "Salt" in step["name"]:
                assert "variables" in step
                assert any(
                    "salt" in key.lower() for key in step["variables"].keys()
                )
                found_salt = True
                break

        assert found_salt, "Salt not found in sign visualization"

    def test_verify_visualization_shows_result(self):
        keygen_response = client.post(
            "/api/generate-keys",
            data={"seed": 0, "param": "hawk-512", "visualize": False},
        )
        keys = keygen_response.json()

        sign_response = client.post(
            "/api/sign",
            data={
                "message": "Test",
                "private_key": keys["private_key"],
                "seed": 0,
                "visualize": False,
            },
        )
        sig_data = sign_response.json()

        response = client.post(
            "/api/verify",
            data={
                "message": "Test",
                "public_key": keys["public_key"],
                "signature": sig_data["signature"],
                "visualize": True,
            },
        )
        data = response.json()

        last_step = data["steps"][-1]
        assert (
            "Result" in last_step["name"] or  # noqa: W504
            "Verification" in last_step["name"]
        )
        assert "variables" in last_step


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
