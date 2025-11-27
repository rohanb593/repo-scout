import os
import shutil
import pandas as pd
import streamlit as st
import requests
from git import Repo
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from io import StringIO

@st.cache_data
def search_github_repositories(query, page, per_page=50):
    url = 'https://api.github.com/search/repositories'
    params = {'q': query, 'page': page, 'per_page': per_page}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()['items']
    else:
        st.error(f"Failed to retrieve repositories. Status code: {response.status_code}")
        return None

def clone_repo(repo_url, clone_dir):
    try:
        if not os.path.exists(clone_dir):
            os.makedirs(clone_dir)
        Repo.clone_from(repo_url, clone_dir, multi_options=["--depth 1"])
    except Exception as e:
        st.error(f"Error cloning repository {repo_url}: {e}")

def count_lines_of_code(directory):
    total_lines = 0
    language_lines = {
        ".java": 0,
        ".py": 0,
        ".js": 0,
        ".rs": 0,
        ".css": 0,
        ".html": 0,
    }
    total_lines_without_spaces_or_comments = 0
    comment_lines = 0
    empty_lines = 0

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_extension = os.path.splitext(file_path)[1]
            if file_extension in language_lines:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            total_lines += 1
                            stripped_line = line.strip()
                            if not stripped_line:
                                empty_lines += 1
                            elif (stripped_line.startswith("//") or stripped_line.startswith("/*") or
                                  stripped_line.startswith("*") or stripped_line.startswith("#") or
                                  stripped_line.startswith("<!--") or stripped_line.startswith("-->")):
                                comment_lines += 1
                            else:
                                total_lines_without_spaces_or_comments += 1
                                language_lines[file_extension] += 1
                except UnicodeDecodeError:
                    pass
                except Exception as e:
                    st.error(f"Error reading file {file_path}: {e}")

    return {
        "total_lines": total_lines,
        "java_lines": language_lines[".java"],
        "python_lines": language_lines[".py"],
        "javascript_lines": language_lines[".js"],
        "rust_lines": language_lines[".rs"],
        "css_lines": language_lines[".css"],
        "html_lines": language_lines[".html"],
        "total_lines_without_spaces_or_comments": total_lines_without_spaces_or_comments,
        "comment_lines": comment_lines,
        "empty_lines": empty_lines
    }

@st.cache_data
def perform_basic_analysis(repositories):
    basic_analysis_results = []
    for repo in repositories:
        basic_analysis_result = {
            "Favorite": "",
            "Name": repo['name'],
            "Description": repo['description'],
            "Stars": repo['stargazers_count'],
            "Forks": repo['forks_count'],
            "Language": repo['language'],
            "Size (KB)": repo['size'],
            "URL": repo['html_url'],  # Include repository URL
            "Created At": repo['created_at'],
            "Updated At": repo['updated_at'],
            "Default Branch": repo['default_branch'],
            "Open Issues": repo['open_issues'],
            "Watchers": repo['watchers'],
            "License": repo['license']['name'] if repo['license'] else None,
        }
        basic_analysis_results.append(basic_analysis_result)

    return basic_analysis_results

def save_to_existing_csv(df, csv_filename):
    df.to_csv(csv_filename, index=False)

def restructure_favorites_df(favorites):
    df = pd.DataFrame(favorites)
    df = df.T  # Transpose the DataFrame to sort by columns instead of rows
    return df

def read_csv_with_error_handling(filename):
    valid_lines = []
    with open(filename, 'r') as file:
        for i, line in enumerate(file):
            try:
                pd.read_csv(StringIO(line))
                valid_lines.append(line)
            except pd.errors.ParserError:
                st.warning(f"Skipping malformed line {i + 1}: {line.strip()}")
            except Exception as e:
                st.error(f"Error reading line {i + 1} from CSV file: {e}")

    if valid_lines:
        return pd.read_csv(StringIO(''.join(valid_lines)))
    else:
        return pd.DataFrame()  # Return empty DataFrame if no valid lines

def perform_detailed_analysis(repositories):
    detailed_analysis_results = []

    for index, repo in repositories.iterrows():
        repo_name = repo['Name']
        repo_url = repo['URL']
        clone_dir = f"./temp_cloned_repos/{repo_name}"

        clone_repo(repo_url, clone_dir)
        if os.path.exists(clone_dir):
            line_counts = count_lines_of_code(clone_dir)
            detailed_analysis_result = {
                "Name": repo_name,
                "Total lines": line_counts['total_lines'],
                "Total lines without spaces or comments": line_counts['total_lines_without_spaces_or_comments'],
                "Java lines": line_counts['java_lines'],
                "Python lines": line_counts['python_lines'],
                "JavaScript lines": line_counts['javascript_lines'],
                "Rust lines": line_counts['rust_lines'],
                "CSS lines": line_counts['css_lines'],
                "HTML lines": line_counts['html_lines'],
                "Comment lines": line_counts['comment_lines'],
                "Empty lines": line_counts['empty_lines']
            }
            detailed_analysis_results.append(detailed_analysis_result)

            shutil.rmtree(clone_dir)
        else:
            st.warning(f"Failed to clone repository {repo_name}.")

    return detailed_analysis_results

def delete_selected_repositories(df, selected_repos):
    updated_df = df[~df['name'].isin(selected_repos['name'])]
    return updated_df

def save_df_to_csv(df, filename):
    df.to_csv(filename, index=False)

def display_aggrid_table(df, key):
    # Ensure 'Favorite' column is at the start
    cols = df.columns.tolist()
    if 'Favorite' in cols:
        cols.insert(0, cols.pop(cols.index('Favorite')))
        df = df[cols]
    
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("Favorite", editable=True) 
    gb.configure_default_column(sortable=True, resizable=True)  

    gridOptions = gb.build()

    grid_return = AgGrid(
        df,
        key= key,
        editable=True,
        gridOptions=gridOptions,
        height=500,
    )

    return grid_return

def sync_favorites_with_selection(df_basic, favorites):
    favorites_set = set(favorites['URL'])  # Use 'URL' for matching
    df_basic['Favorite'] = df_basic['URL'].apply(lambda x: x in favorites_set)
    return df_basic


def update_favorites(df_table, favorites_csv):
    # Read the existing favorites from the CSV file, handling any errors that may occur
    favorites_df = read_csv_with_error_handling(favorites_csv)

    # Extract the current URLs from the df_table and the favorites CSV into sets for easy comparison
    current_urls = set(df_table['URL'])
    favorite_urls = set(favorites_df['URL'])

    # Identify URLs to add: URLs that are marked as favorites in df_table but are not yet in the favorites CSV
    urls_to_add = set(df_table['URL'][df_table['Favorite']]).difference(favorite_urls)

    # Identify URLs to potentially remove: URLs that are not marked as favorites in df_table
    unchecked_urls = set(df_table['URL'][~df_table['Favorite']])

    # Determine URLs to remove: URLs that are currently in favorites but are unchecked in df_table
    urls_to_remove = favorite_urls.intersection(unchecked_urls)

    # Create a DataFrame of the new URLs to add by filtering df_table for URLs in urls_to_add
    df_table_checked = df_table[df_table['URL'].isin(urls_to_add)]

    # Update the favorites DataFrame to remove the URLs that should no longer be favorites   ~
    favorites_df = favorites_df[~favorites_df['URL'].isin(urls_to_remove)]

    # Drop the 'Favorite' column from df_table_checked as it is not needed in the favorites CSV
    df_table_checked = df_table_checked.drop(columns=['Favorite'])
    
    # Concatenate the updated favorites DataFrame with the new entries to add
    updated_favorites_df = pd.concat([favorites_df, df_table_checked])
    
    # Save the updated favorites DataFrame back to the CSV file
    save_to_existing_csv(updated_favorites_df, favorites_csv)


def reorder_columns(grid_data, reference_df):
    # Ensure all necessary columns are present in the grid data
    for col in reference_df.columns:
        if col not in grid_data.columns:
            grid_data[col] = None  # Add missing columns with default None values

    # Reorder columns to match the reference DataFrame
    ordered_data = grid_data[reference_df.columns]
    return ordered_data

def clean_column_names(df):
    df.columns = df.columns.astype(str)
    df.columns = df.columns.str.replace(' ', '_').str.replace('.', '_').str.lower()
    return df


# Set page configuration to full screen
st.set_page_config(layout="wide")

if 'repositories' not in st.session_state:
    st.session_state.repositories = []

if 'detailed_analysis_results' not in st.session_state:
    st.session_state.detailed_analysis_results = []

if 'detailed_analysis_trigger' not in st.session_state:
    st.session_state.detailed_analysis_trigger = False

if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

if 'basic_analysis_results' not in st.session_state:
    st.session_state.basic_analysis_results = []

if 'last_page' not in st.session_state:
    st.session_state.last_page = 1

if 'favorites' not in st.session_state:
    st.session_state.favorites = []

if 'query' not in st.session_state:
    st.session_state.query = ""

menu_options = ["GitHub Repository Search and Code Analysis", "Favorites"]
choice = st.sidebar.selectbox("Select Option", menu_options)

if choice == "GitHub Repository Search and Code Analysis":
    st.title("GitHub Repository Search and Code Analysis")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Enter search query:", value=st.session_state.query)
        
    with col2:
        per_page = st.number_input("Results per page (max 100)", min_value=1, max_value=100, value=100)

    if st.button("Search"):
        st.session_state.query = query
        st.session_state.current_page = 1  # Reset to first page on new search
        repositories = search_github_repositories(st.session_state.query, st.session_state.current_page, per_page=per_page)
        st.session_state.repositories = repositories

    if st.session_state.repositories:
        st.write(f"### Search Results (Page {st.session_state.current_page})")
        basic_analysis_results = perform_basic_analysis(st.session_state.repositories)
        st.session_state.basic_analysis_results = basic_analysis_results

        # Read favorites CSV and update the favorite column
        csv_filename = "favorites.csv"
        try:
            favorites_df = read_csv_with_error_handling(csv_filename)
            df_basic_analysis = sync_favorites_with_selection(pd.DataFrame(st.session_state.basic_analysis_results), favorites_df)
            
        except Exception as e:
            st.error(f"Error reading favorites CSV file: {e}")
            df_basic_analysis = pd.DataFrame(st.session_state.basic_analysis_results)

        # Display basic analysis table and capture selected rows
        grid_return = display_aggrid_table(df_basic_analysis, 'basic_analysis')

        
        columns_order = df_basic_analysis.columns
        df_reordered = reorder_columns(grid_return.data, df_basic_analysis)
        update_favorites(df_reordered, csv_filename)
        


        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Previous Page"):
                if st.session_state.current_page > 1:
                    st.session_state.current_page -= 1
                    repositories = search_github_repositories(st.session_state.query, st.session_state.current_page, per_page=per_page)
                    st.session_state.repositories = repositories
                    st.rerun()  # Rerun with changes after updating state

        with col2:
            if st.button("Next Page"):
                st.session_state.current_page += 1
                repositories = search_github_repositories(st.session_state.query, st.session_state.current_page, per_page=per_page)
                st.session_state.repositories = repositories
                st.rerun()  # Rerun with changes after updating state

        with col3:
            st.write(f"Page {st.session_state.current_page}")

        if st.button("Detailed Analysis"):
            st.session_state.detailed_analysis_trigger = True

    if st.session_state.detailed_analysis_trigger:
        st.write("### Code Analysis - Detailed Information")

        progress_bar = st.progress(0)
        total_repos = len(st.session_state.repositories)
        detailed_analysis_results = []

        for index, repo in enumerate(st.session_state.repositories):
            repo_name = repo['name']
            repo_url = repo['clone_url']
            clone_dir = f"./temp_cloned_repos/{repo_name}"

            clone_repo(repo_url, clone_dir)
            line_counts = count_lines_of_code(clone_dir)
            detailed_analysis_result = {
                "Index": index + 1,  # Adding row index
                "Name": repo_name,
                "Total lines": line_counts['total_lines'],
                "Total lines without spaces or comments": line_counts['total_lines_without_spaces_or_comments'],
                "Java lines": line_counts['java_lines'],
                "Python lines": line_counts['python_lines'],
                "JavaScript lines": line_counts['javascript_lines'],
                "Rust lines": line_counts['rust_lines'],
                "CSS lines": line_counts['css_lines'],
                "HTML lines": line_counts['html_lines'],
                "Comment lines": line_counts['comment_lines'],
                "Empty lines": line_counts['empty_lines']
            }
            detailed_analysis_results.append(detailed_analysis_result)

            progress_bar.progress((index + 1) / total_repos)

            shutil.rmtree(clone_dir)

        # Display detailed analysis results using AgGrid
        if detailed_analysis_results:
            detailed_df = pd.DataFrame(detailed_analysis_results)

            # Configure AgGrid with default and optional columns
            gb_detail = GridOptionsBuilder.from_dataframe(detailed_df)
            gb_detail.configure_default_column(sortable=True, resizable=True)

            # Configure columns to show/hide based on user selection
            
            gb_detail.configure_column("Name", hide=False)
            gb_detail.configure_column("Total lines", hide=False)
            gb_detail.configure_column("Total lines without spaces or comments", hide=False)
            gb_detail.configure_column("Java lines", hide=False)
            gb_detail.configure_column("Python lines", hide=False)
            gb_detail.configure_column("JavaScript lines", hide=False)
            gb_detail.configure_column("Rust lines", hide=False)
            gb_detail.configure_column("CSS lines", hide=False)
            gb_detail.configure_column("HTML lines", hide=False)
            gb_detail.configure_column("Comment lines", hide=False)
            gb_detail.configure_column("Empty lines", hide=False)

            grid_options_detail = gb_detail.build()

            AgGrid(detailed_df, gridOptions=grid_options_detail, enable_enterprise_modules=True, allow_unsafe_jscode=True)

        st.session_state.detailed_analysis_trigger = False
elif choice == "Favorites":
    st.title("Favorites")
    csv_filename = "favorites.csv"
    advanced_csv_filename = "advanced_favorites.csv"

    try:
        
        favorites_df = read_csv_with_error_handling(csv_filename)
        
        if not favorites_df.empty:

            csv_filename = "favorites.csv"
            try:
                favorites_df = read_csv_with_error_handling(csv_filename)
                df_basic_analysis = sync_favorites_with_selection(favorites_df, favorites_df)
            except Exception as e:
                st.error(f"Error reading favorites CSV file: {e}")
                
            st.write("Displaying favorites table...")
            grid_return = display_aggrid_table(df_basic_analysis, 'favourites_basic_analysis')

            if st.button("Update"):
                columns_order = df_basic_analysis.columns
                df_reordered = reorder_columns(grid_return.data, df_basic_analysis)
                update_favorites(df_reordered, csv_filename)
                st.success("Updated successfully")
                st.rerun()
                
            if st.button("Update Advanced Analysis"):
                try:
                    advanced_favorites_df = read_csv_with_error_handling(advanced_csv_filename)
                except Exception as e:
                    st.error(f"Error reading advanced favorites CSV file: {e}")
                    advanced_favorites_df = pd.DataFrame()

                new_favorites_df = favorites_df[~favorites_df['Name'].isin(advanced_favorites_df['Name'])]

                

                if not new_favorites_df.empty:
                    clone_base_dir = "./temp_cloned_repos"
                    os.makedirs(clone_base_dir, exist_ok=True)

                    new_detailed_analysis_results = []
                    cloned_repos_dirs = []

                    for index, repo in new_favorites_df.iterrows():
                        repo_name = repo['Name']
                        repo_url = repo['URL']
                        clone_dir = os.path.join(clone_base_dir, repo_name)

                        clone_repo(repo_url, clone_dir)
                        cloned_repos_dirs.append(clone_dir)

                        line_counts = count_lines_of_code(clone_dir)
                        detailed_analysis_result = {
                            "Name": repo_name,
                            "Total lines": line_counts['total_lines'],
                            "Total lines without spaces or comments": line_counts['total_lines_without_spaces_or_comments'],
                            "Java lines": line_counts['java_lines'],
                            "Python lines": line_counts['python_lines'],
                            "JavaScript lines": line_counts['javascript_lines'],
                            "Rust lines": line_counts['rust_lines'],
                            "CSS lines": line_counts['css_lines'],
                            "HTML lines": line_counts['html_lines'],
                            "Comment lines": line_counts['comment_lines'],
                            "Empty lines": line_counts['empty_lines']
                        }
                        new_detailed_analysis_results.append(detailed_analysis_result)

                    new_detailed_analysis_df = pd.DataFrame(new_detailed_analysis_results)

                    if not new_detailed_analysis_df.empty:
                        advanced_favorites_df = pd.concat([advanced_favorites_df, new_detailed_analysis_df])
                        save_to_existing_csv(advanced_favorites_df, advanced_csv_filename)
                        st.success("Newly added repositories analyzed, results saved to advanced favorites and repositories saved to local device.")

                        # Move cloned repositories to new folder
                        final_clone_dir = "./favorites_repos"
                        os.makedirs(final_clone_dir, exist_ok=True)

                        for clone_dir in cloned_repos_dirs:
                            repo_name = os.path.basename(clone_dir)
                            final_repo_dir = os.path.join(final_clone_dir, repo_name)
                            if os.path.exists(final_repo_dir):
                                shutil.rmtree(final_repo_dir)
                            shutil.move(clone_dir, final_repo_dir)

                    else:
                        st.warning("No new repositories to analyze.")
                else:
                    st.warning("No new repositories found in favorites.")

                removed_repos_df = advanced_favorites_df[~advanced_favorites_df['Name'].isin(favorites_df['Name'])]
                if not removed_repos_df.empty:
                    removed_repos_names = removed_repos_df['Name'].tolist()
                    advanced_favorites_df = advanced_favorites_df[advanced_favorites_df['Name'].isin(favorites_df['Name'])]
                    save_to_existing_csv(advanced_favorites_df, advanced_csv_filename)

                    # Remove repositories from the final_cloned_repos directory
                    final_clone_dir = "./favorites_repos"
                    for repo_name in removed_repos_names:
                        repo_dir = os.path.join(final_clone_dir, repo_name)
                        if os.path.exists(repo_dir):
                            shutil.rmtree(repo_dir)

                            
                # Display advanced favorites after update
                try:
                    advanced_favorites_df = read_csv_with_error_handling(advanced_csv_filename)

                    if not advanced_favorites_df.empty:
                        st.write("Advanced Favorites Analysis Results:")
                        detailed_df = pd.DataFrame(advanced_favorites_df)

                        # Configure AgGrid with default and optional columns
                        gb_detail = GridOptionsBuilder.from_dataframe(detailed_df)
                        gb_detail.configure_default_column(sortable=True, resizable=True)

                        # Configure columns to show/hide based on user selection
                        gb_detail.configure_column("Name", hide=False)
                        gb_detail.configure_column("Total lines", hide=False)
                        gb_detail.configure_column("Total lines without spaces or comments", hide=False)
                        gb_detail.configure_column("Java lines", hide=False)
                        gb_detail.configure_column("Python lines", hide=False)
                        gb_detail.configure_column("JavaScript lines", hide=False)
                        gb_detail.configure_column("Rust lines", hide=False)
                        gb_detail.configure_column("CSS lines", hide=False)
                        gb_detail.configure_column("HTML lines", hide=False)
                        gb_detail.configure_column("Comment lines", hide=False)
                        gb_detail.configure_column("Empty lines", hide=False)
                        grid_options_detail = gb_detail.build()
                        AgGrid(detailed_df, gridOptions=grid_options_detail, enable_enterprise_modules=True, allow_unsafe_jscode=True)
                    else:
                        st.warning("No data found in advanced favorites.")
                except Exception as e:
                    st.error(f"Error reading advanced favorites CSV file: {e}")

        else:
            st.warning("No favorites found.")
    except Exception as e:
        st.error(f"Error reading favorites CSV file: {e}")





