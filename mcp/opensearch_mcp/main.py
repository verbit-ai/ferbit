from fastmcp import FastMCP

mcp = FastMCP("My MCP Server")

app = FastMCP()

@app.tool()
def add(a: int, b: int) -> int:
    print(f"MCP TOOL CALLED: add({a}, {b})")
    result = a + b
    print(f"RESULT: {result}")
    return result

if __name__ == '__main__':
    app.run(transport="sse")