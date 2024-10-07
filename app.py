import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from google.oauth2.service_account import Credentials
import gspread


st.set_page_config(layout="wide")
st.title("Welcome to Data Visualisation Dashboard")


SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


SERVICE_ACCOUNT_FILE = {
    "type": st.secrets["google"]["type"],
    "project_id": st.secrets["google"]["project_id"],
    "private_key_id": st.secrets["google"]["private_key_id"],
    "private_key": st.secrets["google"]["private_key"],
    "client_email": st.secrets["google"]["client_email"],
    "client_id": st.secrets["google"]["client_id"],
    "auth_uri": st.secrets["google"]["auth_uri"],
    "token_uri": st.secrets["google"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["google"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["google"]["client_x509_cert_url"],
    "universe_domain": st.secrets["google"]["universe_domain"]
  }      #'service_account.json'
credentials = Credentials.from_service_account_info(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)

USERNAME = st.secrets["google"]["USERNAME"]
TOKEN = st.secrets["google"]["TOKEN"]

# base URL
BASE_URL = "https://api.github.com"



# fetch pr for a specific repository
@st.cache_data
def fetch_pull_requests(repo_name):
    url = f"{BASE_URL}/repos/{USERNAME}/{repo_name}/pulls?state=all"     
    prs = []
    while url:
        response = requests.get(url, auth=(USERNAME, TOKEN))
        prs += response.json()
        url = response.links.get('next', {}).get('url')  
    return prs

# Function to fetch comments for a specific PR
@st.cache_data
def fetch_pr_comments(repo_name, pr_number):
    url = f"{BASE_URL}/repos/{USERNAME}/{repo_name}/issues/{pr_number}/comments"
    comments = []
    while url:
        response = requests.get(url, auth=(USERNAME, TOKEN))
        comments += response.json()
        url = response.links.get('next', {}).get('url')  
    return comments


@st.cache_data
def get_repo_data(repo_name):
    repo_data = []
    prs = fetch_pull_requests(repo_name)
    for pr in prs:
        comments = fetch_pr_comments(repo_name, pr['number'])
        if comments:
            first_comment_created_at = comments[0]['created_at']
        repo_data.append({
            'PR Number': pr['number'],
            'PR Title': pr['title'],
            'PR State': pr['state'],
            'Created At': pr['created_at'],
            'Updated At': pr['updated_at'],
            'Merged At': pr['merged_at'],
            'First Comment At': first_comment_created_at,
        })

    df = pd.DataFrame(repo_data)
    return df


def get_repo_name_from_url(repo_url):
    repo_name = repo_url.split('/')[-1]
    return repo_name

# Input fields 
repo_url = st.text_input("Enter the GitHub repository URL or the repository name:")
shared_url = st.text_input("Enter the URL for the Google Sheet:")
st.write("Please share the private Google Sheet with this email: pratikingle09@data-visualization-436504.iam.gserviceaccount.com")





if repo_url or shared_url:
    try:
        if repo_url:
            if "github.com" in repo_url:
                repo_name = get_repo_name_from_url(repo_url)
            else:
                repo_name = repo_url 
            
            generateForGithub=True
            repo_df = get_repo_data(repo_name)
            
            repo_df['PR Title'] = repo_df['PR Title']
            
            repo_df['PR Opened Date'] = pd.to_datetime(repo_df['Created At'], utc=True).dt.tz_convert(None)
            
            repo_df['PR Merged Date'] = pd.to_datetime(repo_df['Merged At'], utc=True).dt.tz_convert(None)
            
            repo_df['First Comment At'] = pd.to_datetime(repo_df['First Comment At'], utc=True).dt.tz_convert(None)
            
            repo_df['PR Duration'] = (repo_df['PR Merged Date'] - repo_df['PR Opened Date']).dt.total_seconds() / 3600
            
            repo_df['PR Comments Resolved Duration'] = (repo_df['PR Merged Date'] - repo_df['First Comment At']).dt.total_seconds() / 3600
            
            repo_df['total Comments in Pr'] = repo_df.apply(lambda row: len(fetch_pr_comments(repo_name, row['PR Number'])), axis=1)
        else:
            generateForGithub=False 
         
        if shared_url:
            generateForSheet=True
            # Open Google Sheets and get worksheets
            tables = gc.open_by_url(shared_url)
            worksheets = tables.worksheets()  # Get all worksheets
            worksheet_names = [ws.title for ws in worksheets]  # Extract titles
            selected_sheet = st.selectbox("Select a sheet to visualize:", worksheet_names)

            # Load the selected worksheet into a DataFrame
            selected_worksheet = tables.worksheet(selected_sheet)
            data = selected_worksheet.get_all_values()
            headers = data.pop(0) 
            table = pd.DataFrame(data, columns=headers)

            # Example visualization (you can customize this part)
            st.subheader(f"Data from sheet: {selected_sheet}")
            table['Actual'] = pd.to_numeric(table['ACTUAL'], errors='coerce')  # convert to numeric, 'coerce' will turn invalid parsing into NaN
            table['ESTIMATE'] = pd.to_numeric(table['ESTIMATE'], errors='coerce')
            
            table['Dev Time Difference'] = table['Actual'] - table['ESTIMATE']
        else:
            generateForSheet=False
        
        
        
        
        if st.button("Visualize"):   
            st.write("### Velocity")
            with st.expander("### Velocity: Click to view data source & formula"):
                
                st.write("**Data Source**: Google Sheet")

                st.write("**Formula**:")
                    
                # mathematical formula using LaTeX
                st.latex(r"""
                \text{Sprint Velocity} = \frac{\text{Total Actual Time}}{\text{Total Estimated Time}}
                """)
            col1, col2 = st.columns(2)
            col3, col4 = st.columns(2)
            col6,col7=st.columns(2)
            col8,col9=st.columns(2) 
            
            # Sprint Velocity
            
            if generateForSheet:
                velocity_table = table.dropna(subset=['Actual'])
                total_estimate = velocity_table['ESTIMATE'].sum()
                total_actual = velocity_table['Actual'].sum()
                velocity = total_actual / total_estimate

                time_difference = total_estimate - total_actual
                hours = int(abs(time_difference))
                minutes = int((abs(time_difference) - hours) * 60)

                if velocity > 0:
                    if hours > 0:
                        time_status = f" Ahead of Time by {hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
                    else:
                        time_status = f"**Ahead of Time** by {minutes} minute{'s' if minutes != 1 else ''}"
                elif time_difference < 0:
                    if hours > 0:
                        time_status = f"**Behind Schedule** by {hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
                    else:
                        time_status = f"**Behind Schedule** by {minutes} minute{'s' if minutes != 1 else ''}"
                else:
                    time_status = "**On Time**"

                # Developer contributions
                dev_contributions = table.groupby('ASSIGNEE').agg(
                    total_estimate=('ESTIMATE', 'sum'),
                    total_actual=('Actual', 'sum')
                ).reset_index()
                dev_contributions['velocity'] = dev_contributions['total_actual'] / dev_contributions['total_estimate']

                
                

                
                # <-- custome rule:Velocity -->
                
                
                with col1:
                    velocity_fig = px.bar(
                        x=['Estimated', 'Actual'],
                        y=[total_estimate, total_actual],
                        labels={'x': 'Type of Effort', 'y': 'Effort (hours/story points)'},
                        title='Team Sprint Velocity ' f"Sprint status: {time_status}",
                        text=[total_estimate, total_actual],
                        color=['Estimated', 'Actual'],
                    )
                    velocity_fig.update_layout(bargap=0.7)
                    velocity_fig.update_traces(textposition='outside')
                    velocity_fig.update_layout(showlegend=False, xaxis_title='', yaxis_title='Effort (hours)')
                    st.plotly_chart(velocity_fig)

                with col2:
                    dev_velocity_fig = px.bar(
                        dev_contributions,
                        x='ASSIGNEE',
                        y=['total_estimate', 'total_actual'],
                        barmode='group',
                        title='Individual Developer Velocity',
                        text_auto=True,
                        labels={'variable': 'Type of Effort', 'value': 'Effort (hours)'},
                    )
                    dev_velocity_fig.update_layout(yaxis_title='Effort (hours)', xaxis_title='Developer')
                    st.plotly_chart(dev_velocity_fig)

                        
                        
                # <-- custome rule:Dev Time -->
                
                with col3:
                    st.subheader("Dev Time (Actual)")
                    
                    with st.expander("### Dev Time: Click to view data source & formula"):
                        st.write("**Data Source**: Google Sheet")

                        st.write("**Formula**:")
                        
                        # mathematical formula using LaTeX
                        st.latex(r"""
                        \text{Dev Time} = {\text{Total Actual Time}}
                        """)
                        
                    table['TASK-NAME'] = table['TASK_NAME'].str.slice(0, 10) + '...'
                    dev_time_fig = px.bar(
                        table,
                        x='TASK-NAME',
                        y='Actual',
                        title="Dev Time",
                        hover_data={'TASK-NAME': False,'TASK_NAME': True}
                    )
                    #dev_time_fig.update_traces(marker_color='yellow')
                    dev_time_fig.update_layout(xaxis_title='Task Name', yaxis_title='Dev Time (hours)')
                    st.plotly_chart(dev_time_fig)
                    
                with col6:    
                    table['RISKS'] = table['RISKS'].str.lower()
                    risk_counts = table['RISKS'].value_counts().reset_index()
                    risk_counts.columns = ['Risk Type', 'Count']

                    color_map = {
                    'risk': 'red',      
                    'no risks': 'green',  
                    'not yet identified': 'yellow'    
                    }

                    fig = px.pie(risk_counts, names='Risk Type', values='Count', title='Risk Distribution', color_discrete_map=color_map)
                    fig.update_traces(marker=dict(colors=['green', 'red', 'yellow']))
                    st.plotly_chart(fig)
                with col7:
                    
                    table['SHORT_TASK_NAME'] = table['TASK_NAME'].str.slice(0, 10) + '...'
                    
                    table['PULL'] = 0  
                    table.loc[table['Actual'].isna(), 'PULL'] = 0.1 

                    
                    fig = px.pie(
                    table,
                    names='SHORT_TASK_NAME',  
                    values='ESTIMATE',
                    title='Task Distribution',
                    hover_data={'TASK_NAME': False},  # Prevent hover_data from showing
                    
                    )

                
                    fig.update_traces(
                        pull=table['PULL'],
                        textposition='inside',
                        textinfo='label+value',  
                        textfont_size=14, 
                        hovertemplate='%{customdata[0]}<br>Estimate: %{value}hr',  
                        customdata=table[['TASK_NAME']],  
                        )

                    st.plotly_chart(fig)
                    st.caption("if the task is pulled from rest of the chart it indicates that the task not able to complet in this sprint")

            # <-- custome rule:PR Efficiency Visualization -->
            
            
            # note: Understand how we can see whether the PR completion is done is good or bad
            if generateForGithub:
                with col4:
                    st.subheader("Time for PR (PR Duration)")
                    with st.expander("### Time for PR: Click to view data source & formula"):
                        st.write("**Data Source**: GitHub API")

                        st.write("**Formula**:")
                        
                        # mathematical formula using LaTeX
                        st.latex(r"""
                        \text{Time for PR} = {\text{Last Pr Merged At}} - {\text{First Pr Created At}}
                        """)
                        
                    # Calculate the time between the first PR created and last PR merged
                    first_pr_created_at = repo_df['PR Opened Date'].min()
                    last_pr_merged_at = repo_df['PR Merged Date'].max()

                    # Compute the total duration in hours
                    pr_total_duration = (last_pr_merged_at - first_pr_created_at).total_seconds() / 3600
                    

                    # Show the result
                    st.write(f"**Total time taken for merging all PRs: **")


                    labels = repo_df['PR Title']
                    values = repo_df['PR Duration']
                    
                    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.5)])

                    # Update layout to add text inside the hollow area
                    fig.update_layout(
                        annotations=[dict(text=f"{pr_total_duration:.2f} hours", x=0.5, y=0.5, font_size=20, showarrow=False)]
                    )

                    # Display the chart in Streamlit
                    st.plotly_chart(fig)
                    
        

            # <-- custome rule:Sprint task split -->
            
            if generateForGithub:
                   

                with col8:
                    
                # <-- custome rule:PR Comments Resolution -->
                    
                    st.subheader("Time for PR Comments Resolved")
                    
                    with st.expander("### Time for PR Comments Resolved: Click to view data source & formula"):
                        st.write("**Data Source**: GitHub API")

                        st.write("**Formula**:")
                        
                        # mathematical formula using LaTeX
                        st.latex(r"""
                        \text{Time for PR} = {\text{PR Merged Date}} - {\text{First Comment At}}
                        """)
                        
                        
                    pr_comments_fig = px.bar(
                        repo_df,
                        x='PR Title',
                        y='PR Comments Resolved Duration',
                        title="PR Comments Resolved Duration"
                    )
                    pr_comments_fig.update_layout(bargap=0.5)
                    pr_comments_fig.update_layout(xaxis_title='PR Title', yaxis_title='Resolution Time (hours)')
                    st.plotly_chart(pr_comments_fig)
                    
                    
                with col9:
                    
                # <-- custome rule:PR Comments count -->
                    
                    st.subheader("Number of PR Comments")
                    
                    with st.expander("### Number of PR Comments: Click to view data source & formula"):
                        st.write("**Data Source**: GitHub API")

                        st.write("**Formula**:")
                        
                        # mathematical formula using LaTeX
                        st.latex(r"""
                        \text{Number of PR Comments} = {\text{Total Comments in Pr}}
                        """)
                    
                    pr_comments_fig = px.bar(
                        repo_df,
                        x='PR Title',
                        y='total Comments in Pr',
                        title="PR Comments Count"
                    )
                    pr_comments_fig.update_traces(marker_color='lightgray')
                    pr_comments_fig.update_layout(bargap=0.6)
                    pr_comments_fig.update_layout(xaxis_title='PR Title', yaxis_title='total Comments in Pr', yaxis=dict(
                    tickmode='linear',  
                    tick0=0,            
                    dtick=1           
                ))
                    st.plotly_chart(pr_comments_fig)
                
                
                
            #col10,col11=st.columns(2)    
            
                
            # with col10:
            #     table['Task Clarity'] = table.apply(
            #         lambda row: 'Unclear' if (
            #             'not yet identified' in str(row['REQUIREMENT']).lower() or 
            #             'not yet identified' in str(row['TECHNICAL']).lower())
            #         else 'Clear', axis=1
            #     )

            #     st.subheader("Unclear Tasks")
            #     task_clarity_fig = px.pie(
            #             table,
            #             names='Task Clarity',
            #             title="Clarity of Sprint Tasks",
            #             color='Task Clarity',
            #             color_discrete_map={'Unclear': 'red', 'Clear': 'green'}
            #         )
            #     st.plotly_chart(task_clarity_fig)

                
            
            # with col11:
            #         unclear_tasks = table[table['Task Clarity'] == 'Unclear']
            #         unclear_counts = pd.DataFrame({
            #             'Category': ['Requirement', 'Technical'],
            #             'Unclear Tasks': [
            #                 unclear_tasks['REQUIREMENT'].str.contains('not yet identified', case=False, na=False).sum(),
            #                 unclear_tasks['TECHNICAL'].str.contains('not yet identified', case=False, na=False).sum()
            #             ]
            #         })
                    
            #         st.subheader("Unclear Tasks by Category (Requirement vs Technical)")
            #         unclear_bar_fig = px.bar(
            #             unclear_counts,
            #             x='Category',
            #             y='Unclear Tasks',
            #             title="Number of Unclear Tasks by Category",
            #             text='Unclear Tasks',
            #             color='Category',
            #             color_discrete_map={'Requirement': 'orange', 'Technical': 'blue'}
            #         )

            #         unclear_bar_fig.update_layout(bargap=0.7)
            #         st.plotly_chart(unclear_bar_fig)
                
            # with st.expander("Tasks with Unclear Requirements or Technical Clarity"):
            #         st.write(table[table['Task Clarity'] == 'Unclear'])
                    
            # col12,col13=st.columns(2)       
            # with col12:        
            #     freq_req_change_fig = px.bar(table, 
            #         x='TASK-NAME', 
            #         y='CHANGE LOG', 
            #         title='Requirement Change Frequency',
            #         labels={'Change Log': 'Number of Changes', 'TASK_NAME': 'Task Name'},
            #         color_continuous_scale='Viridis',
            #         hover_data={'TASK_NAME': True, 'TASK-NAME':False}, 
            #         )

            #     freq_req_change_fig.update_layout(bargap=0.3)
            #     freq_req_change_fig.update_traces(marker_color='lightgray')
            #     st.plotly_chart(freq_req_change_fig)
                
            # with col13:
            #     task_counts = table['AD_HOC'].value_counts().reset_index()
            #     task_counts.columns = ['Task Type', 'Count']
            #     task_counts['Task Type'] = task_counts['Task Type'].replace({'yes': 'Ad-Hoc', 'no': 'Planned'})
                
            #     Ad_Hoc_fig = px.pie(task_counts, 
            #                 values='Count', 
            #                 names='Task Type', 
            #                 title='Proportion of Ad-Hoc vs Planned Tasks',
            #                 color_discrete_sequence=['green', 'yellow'])

            #     st.plotly_chart(Ad_Hoc_fig)
                    

                



    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.warning("Please enter both the GitHub repository URL and Google Sheet URL.")
